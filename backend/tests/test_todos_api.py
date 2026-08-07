from datetime import datetime, timedelta, timezone

from app.core.security import hash_password

API_PREFIX = "/api/v1"


def login(client, user_login: str, password: str) -> str:
    response = client.post(f"{API_PREFIX}/auth/login", json={"user_login": user_login, "user_password": password})
    assert response.status_code == 200
    return response.json()["token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_todo_board_lists_tasks_subtasks_and_archive(client, integration_db_session, integration_user):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()
    token = login(client, "worker", "WorkerPass123")

    # Пустой тудулист: ни списков, ни задач.
    board = client.get(f"{API_PREFIX}/todos", headers=auth(token)).json()
    assert board == {"lists": [], "items": []}

    личное = client.post(f"{API_PREFIX}/todo-lists", headers=auth(token), json={"todo_list_name": "Личное"})
    assert личное.status_code == 201
    list_id = личное.json()["item"]["todo_list_id"]

    renamed = client.put(f"{API_PREFIX}/todo-lists/{list_id}", headers=auth(token), json={"todo_list_name": "Дом"})
    assert renamed.status_code == 200
    assert renamed.json()["item"]["todo_list_name"] == "Дом"

    created = client.post(
        f"{API_PREFIX}/todos",
        headers=auth(token),
        json={
            "todo_title": "Купить лампочки",
            "todo_list_id": list_id,
            "todo_note": "две штуки",
            "todo_do_at": datetime.now(timezone.utc).isoformat(),
            "todo_deadline_at": "2020-01-01T18:00:00+03:00",
            "todo_tags": ["дом", "дом", " "],
            "subtasks": [{"todo_subtask_title": "Замерить цоколь"}, {"todo_subtask_title": "Заехать в магазин"}],
        },
    )
    assert created.status_code == 201
    item = created.json()["item"]
    todo_id = item["todo_id"]
    # Пустые и повторяющиеся метки схлопываются.
    assert item["todo_tags"] == ["дом"]
    # Время со смещением приводится к UTC: 01.01.2020 18:00 +03:00 → 15:00Z.
    assert item["todo_deadline_at"].startswith("2020-01-01T15:00:00")
    assert [s["todo_subtask_title"] for s in item["subtasks"]] == ["Замерить цоколь", "Заехать в магазин"]
    assert item["todo_completed"] is False
    assert item["todo_archived"] is False

    # Частичное обновление: галочка на первой подзадаче, дедлайн снимаем (null проходит).
    updated = client.put(
        f"{API_PREFIX}/todos/{todo_id}",
        headers=auth(token),
        json={
            "todo_deadline_at": None,
            "subtasks": [{"todo_subtask_title": "Замерить цоколь", "todo_subtask_done": True}],
        },
    ).json()["item"]
    assert updated["todo_deadline_at"] is None
    assert updated["todo_title"] == "Купить лампочки"  # не присланное поле не затёрлось
    assert [(s["todo_subtask_title"], s["todo_subtask_done"]) for s in updated["subtasks"]] == [("Замерить цоколь", True)]

    # Выполнение проставляет время на сервере, архивация — отдельным флагом.
    completed = client.put(f"{API_PREFIX}/todos/{todo_id}", headers=auth(token), json={"todo_completed": True}).json()["item"]
    assert completed["todo_completed"] is True and completed["todo_completed_at"]
    archived = client.put(f"{API_PREFIX}/todos/{todo_id}", headers=auth(token), json={"todo_archived": True}).json()["item"]
    assert archived["todo_archived"] is True

    # Снятие галочки возвращает задачу из архива в работу.
    reopened = client.put(f"{API_PREFIX}/todos/{todo_id}", headers=auth(token), json={"todo_completed": False}).json()["item"]
    assert reopened["todo_completed"] is False
    assert reopened["todo_archived"] is False

    # Удаление списка не удаляет задачи — они возвращаются во «Входящие».
    assert client.delete(f"{API_PREFIX}/todo-lists/{list_id}", headers=auth(token)).status_code == 204
    board = client.get(f"{API_PREFIX}/todos", headers=auth(token)).json()
    assert board["lists"] == []
    assert board["items"][0]["todo_list_id"] is None

    assert client.delete(f"{API_PREFIX}/todos/{todo_id}", headers=auth(token)).status_code == 204
    assert client.get(f"{API_PREFIX}/todos", headers=auth(token)).json()["items"] == []


def test_todo_reorder_and_isolation_between_users(client, integration_db_session, integration_user, integration_admin):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_admin.user_password = hash_password("AdminPass123")
    integration_db_session.commit()
    worker = login(client, "worker", "WorkerPass123")
    admin = login(client, "admin", "AdminPass123")

    ids = []
    for title in ("Первая", "Вторая", "Третья"):
        ids.append(client.post(f"{API_PREFIX}/todos", headers=auth(worker), json={"todo_title": title}).json()["item"]["todo_id"])

    # Перетаскивание: новый порядок приходит списком позиций, ответ — весь тудулист.
    board = client.put(
        f"{API_PREFIX}/todos/reorder",
        headers=auth(worker),
        json={"items": [{"todo_id": ids[2], "todo_position": 0}, {"todo_id": ids[0], "todo_position": 1}, {"todo_id": ids[1], "todo_position": 2}]},
    ).json()
    assert [i["todo_title"] for i in board["items"]] == ["Третья", "Первая", "Вторая"]

    # Задачи личные: у другого пользователя свой пустой тудулист, чужую не тронуть.
    assert client.get(f"{API_PREFIX}/todos", headers=auth(admin)).json()["items"] == []
    assert client.put(f"{API_PREFIX}/todos/{ids[0]}", headers=auth(admin), json={"todo_title": "Чужая"}).status_code == 404
    assert client.delete(f"{API_PREFIX}/todos/{ids[0]}", headers=auth(admin)).status_code == 404


def test_todo_section_is_grantable(client, integration_db_session, integration_user, integration_admin):
    # Доступ к экрану выдаётся из админки тем же механизмом, что чат/СРМ/прайс.
    integration_admin.user_password = hash_password("AdminPass123")
    integration_db_session.commit()
    admin = login(client, "admin", "AdminPass123")

    response = client.put(
        f"{API_PREFIX}/users/{integration_user.user_id}",
        headers=auth(admin),
        json={"user_sections": ["chat", "todo"]},
    )
    assert response.status_code == 200
    assert response.json()["item"]["user_sections"] == ["chat", "todo"]
