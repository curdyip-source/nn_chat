from app.core.security import hash_password

API_PREFIX = "/api/v1"


def _login(client, login: str, password: str) -> str:
    r = client.post(f"{API_PREFIX}/auth/login", json={"user_login": login, "user_password": password})
    assert r.status_code == 200
    return r.json()["token"]


def test_admin_status_color_persists_across_reference_fetch(client, integration_db_session, integration_admin):
    integration_admin.user_password = hash_password("AdminPass123")
    integration_db_session.commit()
    token = _login(client, "admin", "AdminPass123")
    headers = {"Authorization": f"Bearer {token}"}

    # Берём дефолтный статус заказа «Новый» (цвет orange).
    ref = client.get(f"{API_PREFIX}/reference-data", headers=headers).json()
    novy = next(s for s in ref["statuses"] if s["status_type"] == "orders" and s["status_status"] == "Новый")
    assert novy["status_color"] == "orange"

    # Админ меняет цвет.
    upd = client.put(
        f"{API_PREFIX}/statuses/{novy['status_id']}",
        headers=headers,
        json={"status_type": "orders", "status_status": "Новый", "status_color": "#123456"},
    )
    assert upd.status_code == 200
    assert upd.json()["item"]["status_color"] == "#123456"

    # После повторного обращения к справочникам цвет НЕ откатывается к дефолту.
    ref2 = client.get(f"{API_PREFIX}/reference-data", headers=headers).json()
    novy2 = next(s for s in ref2["statuses"] if s["status_type"] == "orders" and s["status_status"] == "Новый")
    assert novy2["status_color"] == "#123456"
