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


def _first_establishment(client, token: str) -> int:
    ref = client.get(f"{API_PREFIX}/reference-data", headers=auth(token)).json()
    return ref["establishments"][0]["establishment_id"]


def _make_order(client, token: str, establishment_id: int, customer: str) -> int:
    response = client.post(
        f"{API_PREFIX}/orders",
        headers=auth(token),
        json={
            "order_establishment_id": establishment_id,
            "order_customer": customer,
            "items": [{"product_article": "TODO-1", "product_name": "Товар", "order_item_quantity": 1, "order_item_price": "10.00"}],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["item"]["order_id"]


def test_order_todo_is_visible_to_everyone_who_sees_the_order(client, integration_db_session, integration_user, integration_admin):
    # Заказная задача — общая: её видит любой, кому виден заказ, и она едет в карточке
    # заказа (из неё же считается бабл в СРМ).
    integration_admin.user_password = hash_password("AdminPass123")
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()
    admin = login(client, "admin", "AdminPass123")
    worker = login(client, "worker", "WorkerPass123")

    establishment_id = _first_establishment(client, admin)
    order_id = _make_order(client, admin, establishment_id, "Клиент админа")

    created = client.post(
        f"{API_PREFIX}/todos",
        headers=auth(admin),
        json={"todo_title": "Позвонить по заказу", "todo_order_id": order_id, "assignee_user_ids": [integration_user.user_id]},
    )
    assert created.status_code == 201, created.text
    todo = created.json()["item"]
    assert todo["todo_order_id"] == order_id
    assert [a["user_login"] for a in todo["assignees"]] == ["worker"]

    # Задача приезжает внутри карточки заказа.
    order = client.get(f"{API_PREFIX}/orders/{order_id}", headers=auth(admin)).json()["item"]
    assert [t["todo_title"] for t in order["todos"]] == ["Позвонить по заказу"]

    # Ответственный видит чужую задачу в своём тудулисте и может её закрыть.
    board = client.get(f"{API_PREFIX}/todos", headers=auth(worker)).json()
    assert [i["todo_id"] for i in board["items"]] == [todo["todo_id"]]
    done = client.put(f"{API_PREFIX}/todos/{todo['todo_id']}", headers=auth(worker), json={"todo_completed": True})
    assert done.status_code == 200
    assert done.json()["item"]["todo_completed"] is True

    # Но удалить чужую задачу нельзя — только автор или админ.
    assert client.delete(f"{API_PREFIX}/todos/{todo['todo_id']}", headers=auth(worker)).status_code == 403


def test_order_todo_hidden_without_access_to_establishment(client, integration_db_session, integration_user, integration_admin):
    # Нет доступа к складу заказа и не назначен ответственным → задачи не видно,
    # и привязать свою задачу к чужому заказу нельзя.
    integration_admin.user_password = hash_password("AdminPass123")
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()
    admin = login(client, "admin", "AdminPass123")
    worker = login(client, "worker", "WorkerPass123")

    establishment_id = _first_establishment(client, admin)
    order_id = _make_order(client, admin, establishment_id, "Клиент админа")
    todo_id = client.post(
        f"{API_PREFIX}/todos",
        headers=auth(admin),
        json={"todo_title": "Секретная задача", "todo_order_id": order_id},
    ).json()["item"]["todo_id"]

    # У worker нет ролей на складах вообще.
    assert client.get(f"{API_PREFIX}/todos", headers=auth(worker)).json()["items"] == []
    assert client.put(f"{API_PREFIX}/todos/{todo_id}", headers=auth(worker), json={"todo_completed": True}).status_code == 404
    привязка = client.post(
        f"{API_PREFIX}/todos",
        headers=auth(worker),
        json={"todo_title": "Своя", "todo_order_id": order_id},
    )
    assert привязка.status_code == 404


def test_assignee_push_sent_once_on_assignment(client, integration_db_session, integration_user, integration_admin, monkeypatch):
    # Пуш уходит только тем, кого назначили именно этим запросом.
    integration_admin.user_password = hash_password("AdminPass123")
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()
    admin = login(client, "admin", "AdminPass123")

    calls = []
    monkeypatch.setattr(
        "app.services.todos.send_todo_assigned_push_event",
        lambda db, **kwargs: calls.append(kwargs) or 0,
    )

    todo_id = client.post(f"{API_PREFIX}/todos", headers=auth(admin), json={"todo_title": "Задача"}).json()["item"]["todo_id"]
    assert calls == []

    client.put(f"{API_PREFIX}/todos/{todo_id}", headers=auth(admin), json={"assignee_user_ids": [integration_user.user_id]})
    assert len(calls) == 1
    assert calls[0]["recipient_user_ids"] == [integration_user.user_id]

    # Повторное сохранение того же состава пуш не шлёт.
    client.put(f"{API_PREFIX}/todos/{todo_id}", headers=auth(admin), json={"assignee_user_ids": [integration_user.user_id]})
    assert len(calls) == 1
