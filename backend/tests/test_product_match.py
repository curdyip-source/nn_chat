from app.core.security import hash_password

API_PREFIX = "/api/v1"


def _login(client, login: str, password: str) -> str:
    response = client.post(
        f"{API_PREFIX}/auth/login",
        json={"user_login": login, "user_password": password},
    )
    assert response.status_code == 200
    return response.json()["token"]


def _create_product(client, token: str, article: str, name: str, cost: str = "10.00") -> None:
    response = client.post(
        f"{API_PREFIX}/products",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_article": article, "product_name": name, "product_cost_usd": cost},
    )
    assert response.status_code == 201


def test_match_products_by_name(client, integration_db_session, integration_admin):
    integration_admin.user_password = hash_password("AdminPass123")
    integration_db_session.commit()
    token = _login(client, "admin", "AdminPass123")

    _create_product(client, token, "A-1", "Болт М6")
    _create_product(client, token, "A-2", "Гайка М6")
    # Дубль наименования с другим артикулом -> неоднозначность.
    _create_product(client, token, "A-3", "Шайба")
    _create_product(client, token, "A-4", "шайба")

    response = client.post(
        f"{API_PREFIX}/products/match",
        headers={"Authorization": f"Bearer {token}"},
        json={"names": ["Болт М6", "  гайка м6 ", "Шайба", "Неизвестно"]},
    )
    assert response.status_code == 200
    results = {r["query"]: r for r in response.json()["results"]}

    # Точное совпадение (с учётом регистра/пробелов).
    assert results["Болт М6"]["matched"]["product_article"] == "A-1"
    assert results["  гайка м6 "]["matched"]["product_article"] == "A-2"

    # Неоднозначность -> matched=None, два кандидата.
    assert results["Шайба"]["matched"] is None
    assert len(results["Шайба"]["candidates"]) == 2

    # Нет совпадений -> matched=None.
    assert results["Неизвестно"]["matched"] is None


def test_match_requires_auth(client):
    response = client.post(f"{API_PREFIX}/products/match", json={"names": ["x"]})
    assert response.status_code == 401
