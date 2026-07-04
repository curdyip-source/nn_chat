import app.services.messages as messages_service
from openpyxl import Workbook
from app.core.audit_types import EVENT_TYPE_ORDER_CREATE, EVENT_TYPE_ORDER_UPDATE
from app.core.security import hash_password
from app.models import User
from app.models.user_establishment_roles import UserEstablishmentRole
from app.models.reference_data import Establishment, Status


API_PREFIX = "/api/v1"


def login(client, login: str, password: str) -> dict:
    response = client.post(
        f"{API_PREFIX}/auth/login",
        json={
            "user_login": login,
            "user_password": password,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_reference_data_products_messages_and_profile_flow(client, integration_db_session, integration_admin, integration_user):
    integration_admin.user_password = hash_password("AdminPass123")
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()

    user_token = login(client, "worker", "WorkerPass123")["token"]
    admin_token = login(client, "admin", "AdminPass123")["token"]

    reference_response = client.get(f"{API_PREFIX}/reference-data", headers={"Authorization": f"Bearer {user_token}"})
    assert reference_response.status_code == 200
    reference_payload = reference_response.json()
    assert len(reference_payload["establishments"]) >= 3
    assert any(item["order_method_name"] == "Самовывоз" for item in reference_payload["order_methods"])
    avito_method = next(item for item in reference_payload["order_methods"] if item["order_method_name"] == "Авито")
    assert avito_method["order_method_sub_methods"] == ["Авито", "СДЭК", "Яндекс", "5Post", "Почта"]
    assert any(item["status_type"] == "orders" and item["status_status"] == "Новый" for item in reference_payload["statuses"])
    assert any(item["status_type"] == "orders" and item["status_status"] == "Новый" and item["status_color"] == "orange" for item in reference_payload["statuses"])
    assert any(item["status_type"] == "orders" and item["status_status"] == "В обработке" and item["status_color"] == "#3b82f6" for item in reference_payload["statuses"])
    assert any(item["status_type"] == "orders" and item["status_status"] == "На сборку" and item["status_color"] == "#6366f1" for item in reference_payload["statuses"])
    assert any(item["status_type"] == "orders" and item["status_status"] == "Собран" and item["status_color"] == "#0f766e" for item in reference_payload["statuses"])
    assert any(item["status_type"] == "orders" and item["status_status"] == "Выполнен" and item["status_color"] == "#16a34a" for item in reference_payload["statuses"])
    assert any(item["status_type"] == "orders" and item["status_status"] == "Отменен" and item["status_color"] == "red" for item in reference_payload["statuses"])
    assert any(item["status_type"] == "orders" and item["status_status"] == "Возврат" and item["status_color"] == "#9a8b2f" for item in reference_payload["statuses"])
    assert any(item["status_type"] == "order_products" and item["status_status"] == "Не обработан" and item["status_color"] == "gray" for item in reference_payload["statuses"])
    assert any(item["status_type"] == "order_products" and item["status_status"] == "Перемещение" for item in reference_payload["statuses"])
    assert any(item["status_type"] == "order_products" and item["status_status"] == "Заказ поставщику" and item["status_color"] == "orange" for item in reference_payload["statuses"])
    assert any(item["status_type"] == "order_products" and item["status_status"] == "Собрано" and item["status_color"] == "#8b5cf6" for item in reference_payload["statuses"])
    assert any(item["status_type"] == "order_products" and item["status_status"] == "Не будет" and item["status_color"] == "red" for item in reference_payload["statuses"])
    assert any(item["status_type"] == "order_products" and item["status_status"] == "В наличии" for item in reference_payload["statuses"])
    assert any(item["status_type"] == "order_products" and item["status_status"] == "Отгружено" for item in reference_payload["statuses"])
    assert any(item["status_type"] == "order_products" and item["status_status"] == "Отменен" and item["status_color"] == "red" for item in reference_payload["statuses"])
    assert any(item["status_type"] == "order_products" and item["status_status"] == "Возврат" and item["status_color"] == "#9a8b2f" for item in reference_payload["statuses"])
    assert not any(item["status_type"] == "order_products" and item["status_status"] == "Принято на складе" for item in reference_payload["statuses"])
    assert not any(item["status_type"] == "order_products" and item["status_status"] in {"Новый", "Не новый", "В обработке", "Заказ"} for item in reference_payload["statuses"])

    products_response = client.get(f"{API_PREFIX}/products?search=000009", headers={"Authorization": f"Bearer {user_token}"})
    assert products_response.status_code == 200
    assert products_response.json()["pagination"]["total"] >= 1

    create_product_response = client.post(
        f"{API_PREFIX}/products",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "product_article": "TF-TV-40",
            "product_name": "Tom Ford: Tobacco Vanille 40 ml",
            "product_cost_usd": "299.00",
        },
    )
    assert create_product_response.status_code == 201

    fuzzy_products_response = client.get(f"{API_PREFIX}/products?search=to van tob 40", headers={"Authorization": f"Bearer {user_token}"})
    assert fuzzy_products_response.status_code == 200
    assert any(item["product_article"] == "TF-TV-40" for item in fuzzy_products_response.json()["items"])

    create_message_response = client.post(
        f"{API_PREFIX}/messages",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"message_type": "message", "message_text": "hello shared chat"},
    )
    assert create_message_response.status_code == 201
    assert create_message_response.json()["item"]["message_text"] == "hello shared chat"
    message_id = create_message_response.json()["item"]["message_id"]

    update_message_response = client.put(
        f"{API_PREFIX}/messages/{message_id}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"message_text": "hello edited chat"},
    )
    assert update_message_response.status_code == 200
    assert update_message_response.json()["item"]["message_text"] == "hello edited chat"

    upload_attachment_response = client.post(
        f"{API_PREFIX}/message-attachments",
        headers={"Authorization": f"Bearer {user_token}"},
        data={"attachment_kind": "file"},
        files={"file": ("price-list.pdf", b"%PDF-1.7\nchat attachment\n", "application/pdf")},
    )
    assert upload_attachment_response.status_code == 201
    uploaded_attachment = upload_attachment_response.json()["item"]
    assert uploaded_attachment["attachment_kind"] == "file"

    create_file_message_response = client.post(
        f"{API_PREFIX}/messages",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "message_type": "file",
            "attachments": [
                {
                    "attachment_kind": uploaded_attachment["attachment_kind"],
                    "attachment_original_filename": uploaded_attachment["attachment_original_filename"],
                    "attachment_mime_type": uploaded_attachment["attachment_mime_type"],
                    "attachment_storage_key": uploaded_attachment["attachment_storage_key"],
                    "attachment_size_bytes": uploaded_attachment["attachment_size_bytes"],
                }
            ],
        },
    )
    assert create_file_message_response.status_code == 201
    assert len(create_file_message_response.json()["item"]["attachments"]) == 1
    file_message_id = create_file_message_response.json()["item"]["message_id"]
    attachment_id = create_file_message_response.json()["item"]["attachments"][0]["attachment_id"]

    media_attachment_response = client.get(f"/media/message-attachments/{attachment_id}")
    assert media_attachment_response.status_code == 200
    assert media_attachment_response.headers["content-type"] == "application/pdf"
    assert media_attachment_response.content.startswith(b"%PDF-1.7")

    delete_file_message_response = client.delete(
        f"{API_PREFIX}/messages/{file_message_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert delete_file_message_response.status_code == 204

    list_messages_response = client.get(f"{API_PREFIX}/messages?page=1&page_size=10", headers={"Authorization": f"Bearer {admin_token}"})
    assert list_messages_response.status_code == 200
    assert all(item["message_id"] != file_message_id for item in list_messages_response.json()["items"])
    assert list_messages_response.json()["pagination"]["total"] >= 1

    delete_message_response = client.delete(
        f"{API_PREFIX}/messages/{message_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert delete_message_response.status_code == 204

    messages_after_delete_response = client.get(f"{API_PREFIX}/messages?page=1&page_size=20", headers={"Authorization": f"Bearer {admin_token}"})
    assert messages_after_delete_response.status_code == 200
    assert all(item["message_id"] != message_id for item in messages_after_delete_response.json()["items"])

    profile_update_response = client.put(
        f"{API_PREFIX}/users/me/profile",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "user_first_name": "Updated",
            "user_second_name": "Worker",
            "user_age": 26,
            "user_address": "Updated Street",
            "user_profile_photo": "profiles/worker.jpg",
        },
    )
    assert profile_update_response.status_code == 200
    assert profile_update_response.json()["item"]["user_profile_photo"] == "profiles/worker.jpg"

    upload_profile_photo_response = client.post(
        f"{API_PREFIX}/users/me/profile-photo",
        headers={"Authorization": f"Bearer {user_token}"},
        files={"file": ("avatar.jpg", b"fake-jpeg-payload", "image/jpeg")},
    )
    assert upload_profile_photo_response.status_code == 200
    assert upload_profile_photo_response.json()["item"]["user_profile_photo"] == f"profile-photos/{integration_user.user_id}"

    fetch_profile_photo_response = client.get(f"/media/profile-photos/{integration_user.user_id}")
    assert fetch_profile_photo_response.status_code == 200
    assert fetch_profile_photo_response.content == b"fake-jpeg-payload"
    assert fetch_profile_photo_response.headers["content-type"].startswith("image/jpeg")

    device_response = client.post(
        f"{API_PREFIX}/user-devices",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "user_device_token": "ios-device-token-1",
            "user_device_platform": "ios",
        },
    )
    assert device_response.status_code == 201
    assert device_response.json()["item"]["user_device_is_active"] is True


def test_message_create_succeeds_when_push_dispatch_fails(client, integration_db_session, integration_user, monkeypatch):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()

    user_token = login(client, "worker", "WorkerPass123")["token"]

    def failing_push(*args, **kwargs):
        raise RuntimeError("simulated push failure")

    monkeypatch.setattr(messages_service, "send_push_notification_event", failing_push)

    create_message_response = client.post(
        f"{API_PREFIX}/messages",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"message_type": "message", "message_text": "message survives push error"},
    )

    assert create_message_response.status_code == 201
    assert create_message_response.json()["item"]["message_text"] == "message survives push error"


def test_reference_data_restores_missing_default_statuses(client, integration_db_session, integration_user):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.query(Status).delete()
    integration_db_session.add(
        Status(
            status_type="order_products",
            status_status="Перемещение",
            status_color="blue",
            status_owner_user_id=None,
        )
    )
    integration_db_session.commit()

    user_token = login(client, "worker", "WorkerPass123")["token"]

    reference_response = client.get(f"{API_PREFIX}/reference-data", headers={"Authorization": f"Bearer {user_token}"})

    assert reference_response.status_code == 200
    statuses = reference_response.json()["statuses"]
    assert any(item["status_type"] == "orders" and item["status_status"] == "Новый" for item in statuses)
    assert any(item["status_type"] == "orders" and item["status_status"] == "Собран" for item in statuses)
    assert any(item["status_type"] == "inventory" and item["status_status"] == "Новый" for item in statuses)
    assert any(item["status_type"] == "product_registration" and item["status_status"] == "Новый" for item in statuses)
    assert any(item["status_type"] == "order_products" and item["status_status"] == "Не обработан" for item in statuses)
    assert any(item["status_type"] == "order_products" and item["status_status"] == "Перемещение" for item in statuses)
    assert any(item["status_type"] == "order_products" and item["status_status"] == "Собрано" for item in statuses)
    assert not any(item["status_type"] == "order_products" and item["status_status"] == "Принято на складе" for item in statuses)
    assert len({(item["status_type"], item["status_status"]) for item in statuses}) == len(statuses)


def test_reference_data_restores_missing_default_establishments(client, integration_db_session, integration_user):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.query(Establishment).delete()
    integration_db_session.add(
        Establishment(
            establishment_name="Белка",
            establishment_address=None,
            establishment_owner_user_id=None,
        )
    )
    integration_db_session.commit()

    user_token = login(client, "worker", "WorkerPass123")["token"]

    reference_response = client.get(f"{API_PREFIX}/reference-data", headers={"Authorization": f"Bearer {user_token}"})

    assert reference_response.status_code == 200
    establishments = reference_response.json()["establishments"]
    establishment_names = {item["establishment_name"] for item in establishments}
    assert {"Белка", "Окто", "Тула"}.issubset(establishment_names)


def test_order_create_succeeds_when_push_dispatch_fails(client, integration_db_session, integration_user, monkeypatch):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()

    user_token = login(client, "worker", "WorkerPass123")["token"]

    def failing_push(*args, **kwargs):
        raise RuntimeError("simulated push failure")

    monkeypatch.setattr("app.services.orders.send_push_notification_event", failing_push)

    reference_payload = client.get(f"{API_PREFIX}/reference-data", headers={"Authorization": f"Bearer {user_token}"}).json()
    establishment_id = reference_payload["establishments"][0]["establishment_id"]
    order_method_id = reference_payload["order_methods"][0]["order_method_id"]

    create_order_response = client.post(
        f"{API_PREFIX}/orders",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_customer": "Марина",
            "order_info": "Лена",
            "items": [
                {
                    "product_article": "TEST-001",
                    "product_name": "Test Product",
                    "order_item_quantity": 1,
                    "order_item_price": "10.00",
                }
            ],
        },
    )

    assert create_order_response.status_code == 201
    order_payload = create_order_response.json()["item"]
    assert order_payload["order_customer"] == "Марина"

    messages_response = client.get(f"{API_PREFIX}/messages?page=1&page_size=20", headers={"Authorization": f"Bearer {user_token}"})
    assert messages_response.status_code == 200
    assert any(item["message_type"] == "order" and item["message_order_id"] == order_payload["order_id"] for item in messages_response.json()["items"])


def test_order_create_allows_method_with_submethods_without_submethod(client, integration_db_session, integration_user):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()
    user_token = login(client, "worker", "WorkerPass123")["token"]

    reference_payload = client.get(f"{API_PREFIX}/reference-data", headers={"Authorization": f"Bearer {user_token}"}).json()
    establishment_id = reference_payload["establishments"][0]["establishment_id"]
    avito_method = next(item for item in reference_payload["order_methods"] if item["order_method_name"] == "Авито")
    assert avito_method["order_method_sub_methods"]

    create_order_response = client.post(
        f"{API_PREFIX}/orders",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": avito_method["order_method_id"],
            "order_contact_method": "WA",
            "order_customer": "Марина",
            "order_info": "Лена",
            "items": [
                {
                    "product_article": "TEST-CONTACT-001",
                    "product_name": "Test Product",
                    "order_item_quantity": 1,
                    "order_item_price": "10.00",
                }
            ],
        },
    )

    assert create_order_response.status_code == 201
    order_payload = create_order_response.json()["item"]
    assert order_payload["order_sub_method"] is None
    assert order_payload["order_contact_method"] == "WA"


def test_order_create_rejects_unknown_contact_method(client, integration_db_session, integration_user):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()
    user_token = login(client, "worker", "WorkerPass123")["token"]

    reference_payload = client.get(f"{API_PREFIX}/reference-data", headers={"Authorization": f"Bearer {user_token}"}).json()
    establishment_id = reference_payload["establishments"][0]["establishment_id"]
    order_method_id = reference_payload["order_methods"][0]["order_method_id"]

    create_order_response = client.post(
        f"{API_PREFIX}/orders",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_contact_method": "ZZ",
            "order_customer": "Марина",
            "order_info": "Лена",
            "items": [
                {
                    "product_article": "TEST-CONTACT-002",
                    "product_name": "Test Product",
                    "order_item_quantity": 1,
                    "order_item_price": "10.00",
                }
            ],
        },
    )

    assert create_order_response.status_code == 400


def test_order_inventory_and_product_registration_create_messages(client, integration_db_session, integration_admin, integration_user):
    integration_admin.user_password = hash_password("AdminPass123")
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()

    user_token = login(client, "worker", "WorkerPass123")["token"]

    reference_payload = client.get(f"{API_PREFIX}/reference-data", headers={"Authorization": f"Bearer {user_token}"}).json()
    establishment_id = reference_payload["establishments"][0]["establishment_id"]
    destination_establishment_id = reference_payload["establishments"][1]["establishment_id"]
    avito_method = next(item for item in reference_payload["order_methods"] if item["order_method_name"] == "Авито")
    order_method_id = avito_method["order_method_id"]

    order_response = client.post(
        f"{API_PREFIX}/orders",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_sub_method": "СДЭК",
            "order_customer": "Марина",
            "order_info": "г. Москва, улица Восьмая 6",
            "items": [
                {
                    "product_article": "NEW-001",
                    "product_name": "New Product",
                    "order_item_quantity": 2,
                    "order_item_price": "19.99",
                }
            ],
        },
    )
    assert order_response.status_code == 201
    order_payload = order_response.json()["item"]
    assert order_payload["order_customer"] == "Марина"
    assert order_payload["order_method_name"] == "Авито"
    assert order_payload["order_sub_method"] == "СДЭК"
    assert order_payload["message_id"]
    order_id = order_payload["order_id"]

    comment_response = client.post(
        f"{API_PREFIX}/orders/{order_id}/comments",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"order_comment_text": "Позвонить перед доставкой"},
    )
    assert comment_response.status_code == 201
    comment_payload = comment_response.json()["item"]
    assert comment_payload["order_comment_text"] == "Позвонить перед доставкой"
    assert comment_payload["order_comment_owner_user_id"] == integration_user.user_id
    assert "order_comment_owner_first_name" in comment_payload
    assert "order_comment_owner_second_name" in comment_payload

    upload_order_comment_attachment_response = client.post(
        f"{API_PREFIX}/message-attachments",
        headers={"Authorization": f"Bearer {user_token}"},
        data={"attachment_kind": "photo"},
        files={"file": ("order-photo.jpg", b"fake-order-photo", "image/jpeg")},
    )
    assert upload_order_comment_attachment_response.status_code == 201
    uploaded_order_comment_attachment = upload_order_comment_attachment_response.json()["item"]

    attachment_comment_response = client.post(
        f"{API_PREFIX}/orders/{order_id}/comments",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "attachments": [
                {
                    "attachment_kind": uploaded_order_comment_attachment["attachment_kind"],
                    "attachment_original_filename": uploaded_order_comment_attachment["attachment_original_filename"],
                    "attachment_mime_type": uploaded_order_comment_attachment["attachment_mime_type"],
                    "attachment_storage_key": uploaded_order_comment_attachment["attachment_storage_key"],
                    "attachment_size_bytes": uploaded_order_comment_attachment["attachment_size_bytes"],
                }
            ]
        },
    )
    assert attachment_comment_response.status_code == 201
    attachment_comment_payload = attachment_comment_response.json()["item"]
    assert attachment_comment_payload["order_comment_text"] == ""
    assert len(attachment_comment_payload["attachments"]) == 1
    order_comment_attachment_id = attachment_comment_payload["attachments"][0]["attachment_id"]

    order_comment_media_response = client.get(f"/media/order-comment-attachments/{order_comment_attachment_id}")
    assert order_comment_media_response.status_code == 200
    assert order_comment_media_response.headers["content-type"].startswith("image/jpeg")
    assert order_comment_media_response.content == b"fake-order-photo"

    order_detail_response = client.get(f"{API_PREFIX}/orders/{order_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert order_detail_response.status_code == 200
    assert len(order_detail_response.json()["item"]["items"]) == 1
    assert len(order_detail_response.json()["item"]["comments"]) == 2
    assert len(order_detail_response.json()["item"]["comments"][1]["attachments"]) == 1
    assert order_detail_response.json()["item"]["items"][0]["order_item_status"] == "Не обработан"
    assert order_detail_response.json()["item"]["items"][0]["order_item_status_color"] == "gray"

    order_status_id = next(item for item in reference_payload["statuses"] if item["status_type"] == "orders" and item["status_status"] == "В обработке")["status_id"]
    order_product_status_id = next(item for item in reference_payload["statuses"] if item["status_type"] == "order_products" and item["status_status"] == "Заказ поставщику")["status_id"]
    updated_order_response = client.put(
        f"{API_PREFIX}/orders/{order_id}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_sub_method": "Авито",
            "order_customer": "Марина Петрова",
            "order_info": "г. Москва, улица Девятая 7",
            "order_status_id": order_status_id,
            "items": [
                {
                    "product_article": "NEW-001",
                    "product_name": "New Product",
                    "order_item_quantity": 5,
                    "order_item_price": "21.50",
                    "order_item_status_id": order_product_status_id,
                    "order_item_supplier": "ООО Восток",
                },
                {
                    "product_article": "NEW-002",
                    "product_name": "Second Product",
                    "order_item_quantity": 1,
                    "order_item_price": "7.00",
                },
            ],
        },
    )
    assert updated_order_response.status_code == 200
    updated_order_payload = updated_order_response.json()["item"]
    assert updated_order_payload["order_status"] == "В обработке"
    assert updated_order_payload["order_customer"] == "Марина Петрова"
    assert updated_order_payload["order_sub_method"] == "Авито"
    assert len(updated_order_payload["items"]) == 2
    assert updated_order_payload["items"][0]["order_item_status"] == "Заказ поставщику"
    assert updated_order_payload["items"][0]["order_item_supplier"] == "ООО Восток"

    supplier_contacts_response = client.get(
        f"{API_PREFIX}/contacts?contact_type=supplier&search=Восток",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert supplier_contacts_response.status_code == 200
    assert any(item["contact_name"] == "ООО Восток" for item in supplier_contacts_response.json()["items"])

    movement_status_id = next(item for item in reference_payload["statuses"] if item["status_type"] == "order_products" and item["status_status"] == "Перемещение")["status_id"]
    movement_update_response = client.put(
        f"{API_PREFIX}/orders/{order_id}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_sub_method": "Авито",
            "order_customer": "Марина Петрова",
            "order_info": "г. Москва, улица Девятая 7",
            "order_status_id": order_status_id,
            "items": [
                {
                    "product_article": "NEW-001",
                    "product_name": "New Product",
                    "order_item_quantity": 5,
                    "order_item_price": "21.50",
                    "order_item_status_id": movement_status_id,
                    "order_item_source_establishment_id": establishment_id,
                    "order_item_destination_establishment_id": destination_establishment_id,
                    "order_item_checkpoint_started": True,
                }
            ],
        },
    )
    assert movement_update_response.status_code == 200
    movement_item = movement_update_response.json()["item"]["items"][0]
    assert movement_item["order_item_status"] == "Перемещение"
    assert movement_item["order_item_source_establishment_id"] == establishment_id
    assert movement_item["order_item_destination_establishment_id"] == destination_establishment_id
    assert movement_item["order_item_checkpoint_started"] is True
    assert movement_item["order_item_checkpoint_completed"] is False

    inventory_response = client.post(
        f"{API_PREFIX}/inventories",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "inventory_establishment_id": establishment_id,
            "items": [
                {
                    "product_id": 1,
                    "inventory_item_quantity": 3,
                    "inventory_item_cost": "10.00",
                }
            ],
        },
    )
    assert inventory_response.status_code == 201
    assert inventory_response.json()["item"]["inventory_status"] == "Новый"
    assert inventory_response.json()["item"]["inventory_supplier"] is None

    product_registration_response = client.post(
        f"{API_PREFIX}/product-registrations",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "product_registration_establishment_id": establishment_id,
            "product_registration_supplier": "ЗАО Север",
            "items": [
                {
                    "product_id": 1,
                    "product_registration_item_quantity": 4,
                    "product_registration_item_cost": "11.00",
                }
            ],
        },
    )
    assert product_registration_response.status_code == 201
    assert product_registration_response.json()["item"]["product_registration_status"] == "Новый"
    assert product_registration_response.json()["item"]["product_registration_supplier"] == "ЗАО Север"

    messages_response = client.get(f"{API_PREFIX}/messages?page=1&page_size=20", headers={"Authorization": f"Bearer {user_token}"})
    assert messages_response.status_code == 200
    messages_payload = messages_response.json()["items"]
    message_types = {item["message_type"] for item in messages_payload}
    assert {"order", "inventory", "product_registration"}.issubset(message_types)
    assert any(item["message_type"] == "order" and item["message_status"] == "В обработке" and item["message_status_color"] == "#3b82f6" for item in messages_payload)


def test_order_audit_payload_contains_field_and_item_changes(client, integration_db_session, integration_admin, integration_user):
    integration_admin.user_password = hash_password("AdminPass123")
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()

    admin_token = login(client, "admin", "AdminPass123")["token"]
    user_token = login(client, "worker", "WorkerPass123")["token"]

    reference_payload = client.get(f"{API_PREFIX}/reference-data", headers={"Authorization": f"Bearer {user_token}"}).json()
    establishment_id = reference_payload["establishments"][0]["establishment_id"]
    order_method_id = next(item for item in reference_payload["order_methods"] if item["order_method_name"] == "Авито")["order_method_id"]
    new_status_id = next(item for item in reference_payload["statuses"] if item["status_type"] == "orders" and item["status_status"] == "Новый")["status_id"]
    processing_status_id = next(item for item in reference_payload["statuses"] if item["status_type"] == "orders" and item["status_status"] == "В обработке")["status_id"]
    order_product_status_id = next(item for item in reference_payload["statuses"] if item["status_type"] == "order_products" and item["status_status"] == "Заказ поставщику")["status_id"]

    create_response = client.post(
        f"{API_PREFIX}/orders",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_sub_method": "СДЭК",
            "order_customer": "Марина",
            "order_info": "Москва, первая линия",
            "items": [
                {
                    "product_article": "AUD-001",
                    "product_name": "Audit Product",
                    "order_item_quantity": 2,
                    "order_item_price": "19.99",
                }
            ],
        },
    )
    assert create_response.status_code == 201
    order_id = create_response.json()["item"]["order_id"]

    create_audit_response = client.get(
        f"{API_PREFIX}/audit-events?entity_type=order&entity_id={order_id}&event_type={EVENT_TYPE_ORDER_CREATE}&page=1&page_size=10",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_audit_response.status_code == 200
    create_audit_item = create_audit_response.json()["items"][0]
    assert create_audit_item["actor_user_login"] == "worker"
    assert create_audit_item["event_payload"]["items_count"] == 1
    assert create_audit_item["event_payload"]["order"]["order_customer"] == "Марина"

    update_response = client.put(
        f"{API_PREFIX}/orders/{order_id}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_sub_method": "Авито",
            "order_customer": "Марина Петрова",
            "order_info": "Москва, вторая линия",
            "order_status_id": processing_status_id,
            "items": [
                {
                    "product_article": "AUD-001",
                    "product_name": "Audit Product",
                    "order_item_quantity": 5,
                    "order_item_price": "21.50",
                    "order_item_status_id": order_product_status_id,
                },
                {
                    "product_article": "AUD-002",
                    "product_name": "Second Audit Product",
                    "order_item_quantity": 1,
                    "order_item_price": "7.00",
                },
            ],
        },
    )
    assert update_response.status_code == 200

    update_audit_response = client.get(
        f"{API_PREFIX}/audit-events?entity_type=order&entity_id={order_id}&event_type={EVENT_TYPE_ORDER_UPDATE}&page=1&page_size=10",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_audit_response.status_code == 200
    update_audit_item = update_audit_response.json()["items"][0]
    changed_fields = update_audit_item["event_payload"]["changed_fields"]
    assert changed_fields["order_customer"] == {"from": "Марина", "to": "Марина Петрова"}
    assert changed_fields["order_status"] == {"from": "Новый", "to": "В обработке"}
    assert update_audit_item["event_payload"]["items"]["before_count"] == 1
    assert update_audit_item["event_payload"]["items"]["after_count"] == 2
    assert len(update_audit_item["event_payload"]["items"]["added"]) == 1
    assert len(update_audit_item["event_payload"]["items"]["updated"]) == 1
    assert update_audit_item["event_payload"]["items"]["updated"][0]["changes"]["order_item_quantity"] == {"from": 2, "to": 5}
    assert update_audit_item["event_payload"]["items"]["updated"][0]["changes"]["order_item_price"] == {"from": "19.99", "to": "21.50"}

    status_update_response = client.put(
        f"{API_PREFIX}/orders/{order_id}/status",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"order_status_id": new_status_id},
    )
    assert status_update_response.status_code == 200

    status_audit_response = client.get(
        f"{API_PREFIX}/audit-events?entity_type=order&entity_id={order_id}&event_type={EVENT_TYPE_ORDER_UPDATE}&page=1&page_size=10",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert status_audit_response.status_code == 200
    status_audit_item = status_audit_response.json()["items"][0]
    assert status_audit_item["event_payload"]["changed_fields"]["order_status"] == {"from": "В обработке", "to": "Новый"}
    assert status_audit_item["event_payload"]["items"]["added"] == []
    assert status_audit_item["event_payload"]["items"]["removed"] == []
    assert status_audit_item["event_payload"]["items"]["updated"] == []


def test_admin_activation_sets_verified_user(client, integration_db_session, integration_admin):
    integration_admin.user_password = hash_password("AdminPass123")
    integration_db_session.commit()

    admin_token = login(client, "admin", "AdminPass123")["token"]
    create_response = client.post(
        f"{API_PREFIX}/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "user_login": "inactive_new_user",
            "user_password": "UserPass123",
            "user_admin": False,
            "user_active": False,
            "user_first_name": "Inactive",
            "user_second_name": "New",
            "user_age": 22,
            "user_address": "Zero Street",
        },
    )
    assert create_response.status_code == 201
    created_user_id = create_response.json()["item"]["user_id"]

    activate_response = client.put(
        f"{API_PREFIX}/users/{created_user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"user_active": True},
    )
    assert activate_response.status_code == 200
    assert activate_response.json()["item"]["user_verified_user_id"] == integration_admin.user_id

    created_user = integration_db_session.query(User).filter(User.user_id == created_user_id).one()
    assert created_user.user_verified_user_id == integration_admin.user_id


def test_order_info_can_be_empty_on_create_and_update(client, integration_db_session, integration_admin, integration_user):
    integration_admin.user_password = hash_password("AdminPass123")
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()

    user_token = login(client, "worker", "WorkerPass123")["token"]

    reference_payload = client.get(f"{API_PREFIX}/reference-data", headers={"Authorization": f"Bearer {user_token}"}).json()
    establishment_id = reference_payload["establishments"][0]["establishment_id"]
    order_method_id = reference_payload["order_methods"][0]["order_method_id"]
    order_status_id = next(item for item in reference_payload["statuses"] if item["status_type"] == "orders" and item["status_status"] == "Новый")["status_id"]

    create_response = client.post(
        f"{API_PREFIX}/orders",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_customer": "Марина",
            "order_info": "",
            "items": [
                {
                    "product_article": "EMPTY-INFO-001",
                    "product_name": "Test Product",
                    "order_item_quantity": 1,
                    "order_item_price": "10.00",
                }
            ],
        },
    )
    assert create_response.status_code == 201
    created_order = create_response.json()["item"]
    assert created_order["order_info"] == ""

    update_response = client.put(
        f"{API_PREFIX}/orders/{created_order['order_id']}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_customer": "Марина",
            "order_info": "",
            "order_status_id": order_status_id,
            "items": [
                {
                    "product_article": "EMPTY-INFO-001",
                    "product_name": "Test Product",
                    "order_item_quantity": 1,
                    "order_item_price": "10.00",
                }
            ],
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["item"]["order_info"] == ""


def test_admin_can_import_products_from_xlsx(client, integration_db_session, integration_admin):
    integration_admin.user_password = hash_password("AdminPass123")
    integration_db_session.commit()

    admin_token = login(client, "admin", "AdminPass123")["token"]

    existing_product_response = client.post(
        f"{API_PREFIX}/products",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "product_article": "EXIST-1",
            "product_name": "Old Name",
            "product_cost_usd": "7.00",
        },
    )
    assert existing_product_response.status_code == 201

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Артикул", "Наименование", "ignored", "cost_usd"])
    sheet.append([None, "Секция", None, None])
    sheet.append(["EXIST-1", "New Name", None, "8,50"])
    sheet.append(["000777", "Imported Product", None, 12.34])

    from io import BytesIO

    buffer = BytesIO()
    workbook.save(buffer)

    import_response = client.post(
        f"{API_PREFIX}/products/import-xlsx",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={"file": ("products.xlsx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert import_response.status_code == 200
    payload = import_response.json()["item"]
    assert payload["status"] in {"queued", "running"}
    assert payload["total_rows"] == 3
    job_id = payload["job_id"]

    final_payload = None
    for _ in range(40):
        status_response = client.get(f"{API_PREFIX}/products/import-xlsx/{job_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert status_response.status_code == 200
        final_payload = status_response.json()["item"]
        if final_payload["status"] in {"completed", "failed"}:
            break
        import time
        time.sleep(0.05)

    assert final_payload is not None
    assert final_payload["status"] == "completed"
    assert final_payload["created"] == 1
    assert final_payload["updated"] == 1
    assert final_payload["skipped"] == 1

    products_response = client.get(f"{API_PREFIX}/products?search=000777", headers={"Authorization": f"Bearer {admin_token}"})
    assert products_response.status_code == 200
    created_product = next(item for item in products_response.json()["items"] if item["product_article"] == "000777")
    assert created_product["product_name"] == "Imported Product"
    assert created_product["product_cost_usd"] == "12.34"

    updated_response = client.get(f"{API_PREFIX}/products?search=EXIST-1", headers={"Authorization": f"Bearer {admin_token}"})
    assert updated_response.status_code == 200
    updated_product = next(item for item in updated_response.json()["items"] if item["product_article"] == "EXIST-1")
    assert updated_product["product_name"] == "New Name"
    assert updated_product["product_cost_usd"] == "8.50"

def _add_user(db_session, *, login, first_name, second_name, active=True, password="WorkerPass123"):
    user = User(
        user_login=login,
        user_password=hash_password(password),
        user_admin=False,
        user_active=active,
        user_first_name=first_name,
        user_second_name=second_name,
        user_age=30,
        user_address="Somewhere",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_chat_participants_returns_active_users_for_non_admin(client, integration_db_session, integration_user):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()
    manager = _add_user(integration_db_session, login="manager", first_name="Stanislav", second_name="Kirillov")
    _add_user(integration_db_session, login="ghost", first_name="In", second_name="Active", active=False)

    user_token = login(client, "worker", "WorkerPass123")["token"]
    response = client.get(f"{API_PREFIX}/users/participants", headers={"Authorization": f"Bearer {user_token}"})

    assert response.status_code == 200
    logins = {item["user_login"] for item in response.json()["items"]}
    assert "worker" in logins
    assert "manager" in logins
    assert "ghost" not in logins
    manager_item = next(item for item in response.json()["items"] if item["user_login"] == "manager")
    assert manager_item["user_first_name"] == "Stanislav"
    assert manager_item["user_second_name"] == "Kirillov"
    assert "user_id" in manager_item


def test_message_create_sends_mention_push_to_active_mentioned_users(client, integration_db_session, integration_user, monkeypatch):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()
    manager = _add_user(integration_db_session, login="manager", first_name="Stanislav", second_name="Kirillov")
    ghost = _add_user(integration_db_session, login="ghost", first_name="In", second_name="Active", active=False)

    captured = {}

    def fake_mention_push(db, *, recipient_user_ids, sender_name, context, entity_id):
        captured["recipient_user_ids"] = recipient_user_ids
        captured["context"] = context
        captured["sender_name"] = sender_name
        return len(recipient_user_ids)

    monkeypatch.setattr("app.services.messages.send_mention_push_event", fake_mention_push)

    user_token = login(client, "worker", "WorkerPass123")["token"]
    response = client.post(
        f"{API_PREFIX}/messages",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "message_type": "message",
            "message_text": "@Kirillov Stanislav привет",
            "mentioned_user_ids": [manager.user_id, ghost.user_id, integration_user.user_id],
        },
    )

    assert response.status_code == 201
    assert captured["recipient_user_ids"] == [manager.user_id]
    assert captured["context"] == "chat"
    assert "Worker" in captured["sender_name"]


def test_order_update_sends_push_when_items_added_or_removed(client, integration_db_session, integration_user, monkeypatch):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()
    user_token = login(client, "worker", "WorkerPass123")["token"]

    reference_payload = client.get(f"{API_PREFIX}/reference-data", headers={"Authorization": f"Bearer {user_token}"}).json()
    establishment_id = reference_payload["establishments"][0]["establishment_id"]
    order_method_id = next(item for item in reference_payload["order_methods"] if item["order_method_name"] == "Самовывоз")["order_method_id"]

    def item(article, name):
        return {"product_article": article, "product_name": name, "order_item_quantity": 1, "order_item_price": "10.00"}

    create_response = client.post(
        f"{API_PREFIX}/orders",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_customer": "Марина",
            "order_info": "Лена",
            "items": [item("CHG-1", "First")],
        },
    )
    assert create_response.status_code == 201
    order = create_response.json()["item"]

    captured = []
    monkeypatch.setattr(
        "app.services.orders.send_order_change_push_event",
        lambda db, **kwargs: captured.append(kwargs) or 1,
    )

    base_update = {
        "order_establishment_id": establishment_id,
        "order_method_id": order_method_id,
        "order_customer": "Марина",
        "order_info": "Лена",
        "order_status_id": order["order_status_id"],
    }

    add_response = client.put(
        f"{API_PREFIX}/orders/{order['order_id']}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={**base_update, "items": [item("CHG-1", "First"), item("CHG-2", "Second")]},
    )
    assert add_response.status_code == 200
    assert captured[-1]["added_count"] == 1
    assert captured[-1]["removed_count"] == 0

    remove_response = client.put(
        f"{API_PREFIX}/orders/{order['order_id']}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={**base_update, "items": [item("CHG-1", "First")]},
    )
    assert remove_response.status_code == 200
    assert captured[-1]["added_count"] == 0
    assert captured[-1]["removed_count"] == 1


def test_order_update_does_not_push_when_items_unchanged(client, integration_db_session, integration_user, monkeypatch):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()
    user_token = login(client, "worker", "WorkerPass123")["token"]

    reference_payload = client.get(f"{API_PREFIX}/reference-data", headers={"Authorization": f"Bearer {user_token}"}).json()
    establishment_id = reference_payload["establishments"][0]["establishment_id"]
    order_method_id = next(item for item in reference_payload["order_methods"] if item["order_method_name"] == "Самовывоз")["order_method_id"]

    create_response = client.post(
        f"{API_PREFIX}/orders",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_customer": "Марина",
            "order_info": "Лена",
            "items": [{"product_article": "UNCH-1", "product_name": "Item", "order_item_quantity": 1, "order_item_price": "10.00"}],
        },
    )
    assert create_response.status_code == 201
    order = create_response.json()["item"]

    captured = []
    monkeypatch.setattr(
        "app.services.orders.send_order_change_push_event",
        lambda db, **kwargs: captured.append(kwargs) or 1,
    )

    update_response = client.put(
        f"{API_PREFIX}/orders/{order['order_id']}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_customer": "Марина Новая",
            "order_info": "Лена",
            "order_status_id": order["order_status_id"],
            "items": [{"product_article": "UNCH-1", "product_name": "Item", "order_item_quantity": 5, "order_item_price": "20.00"}],
        },
    )
    assert update_response.status_code == 200
    assert captured == []


def _create_simple_order(client, token):
    ref = client.get(f"{API_PREFIX}/reference-data", headers={"Authorization": f"Bearer {token}"}).json()
    establishment_id = ref["establishments"][0]["establishment_id"]
    order_method_id = ref["order_methods"][0]["order_method_id"]
    response = client.post(
        f"{API_PREFIX}/orders",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_customer": "Клиент",
            "order_info": "инфо",
            "items": [{"product_article": "DEL-001", "product_name": "Del Product", "order_item_quantity": 1, "order_item_price": "10.00"}],
        },
    )
    assert response.status_code == 201
    return response.json()["item"]["order_id"]


def test_delete_order_by_owner_removes_order_and_tombstones_card(client, integration_db_session, integration_user):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()
    token = login(client, "worker", "WorkerPass123")["token"]
    order_id = _create_simple_order(client, token)

    messages = client.get(f"{API_PREFIX}/messages?page=1&page_size=20", headers={"Authorization": f"Bearer {token}"}).json()["items"]
    assert any(m["message_type"] == "order" and m["message_order_id"] == order_id for m in messages)

    delete_response = client.delete(f"{API_PREFIX}/orders/{order_id}", headers={"Authorization": f"Bearer {token}"})
    assert delete_response.status_code == 204

    assert client.get(f"{API_PREFIX}/orders/{order_id}", headers={"Authorization": f"Bearer {token}"}).status_code == 404
    messages_after = client.get(f"{API_PREFIX}/messages?page=1&page_size=20", headers={"Authorization": f"Bearer {token}"}).json()["items"]
    assert not any(m.get("message_order_id") == order_id for m in messages_after)


def test_delete_order_forbidden_for_non_owner_non_admin(client, integration_db_session, integration_user):
    integration_user.user_password = hash_password("WorkerPass123")
    other = User(user_login="worker2", user_password=hash_password("Worker2Pass123"), user_admin=False, user_active=True, user_first_name="Worker2", user_second_name="User", user_age=27, user_address="Street 2")
    integration_db_session.add(other)
    integration_db_session.commit()
    owner_token = login(client, "worker", "WorkerPass123")["token"]
    other_token = login(client, "worker2", "Worker2Pass123")["token"]

    est_id = _first_establishment_ids(client, owner_token, 1)[0]
    order_id = _create_simple_order(client, owner_token)
    # worker2 получает доступ к складу заказа (видит его), но не владелец → удаление 403.
    integration_db_session.add(
        UserEstablishmentRole(
            user_establishment_role_user_id=other.user_id,
            user_establishment_role_establishment_id=est_id,
            user_establishment_role_role="editor",
        )
    )
    integration_db_session.commit()
    forbidden = client.delete(f"{API_PREFIX}/orders/{order_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert forbidden.status_code == 403
    assert client.get(f"{API_PREFIX}/orders/{order_id}", headers={"Authorization": f"Bearer {owner_token}"}).status_code == 200


def test_delete_order_allowed_for_admin(client, integration_db_session, integration_user, integration_admin):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_admin.user_password = hash_password("AdminPass123")
    integration_db_session.commit()
    owner_token = login(client, "worker", "WorkerPass123")["token"]
    admin_token = login(client, "admin", "AdminPass123")["token"]

    order_id = _create_simple_order(client, owner_token)
    assert client.delete(f"{API_PREFIX}/orders/{order_id}", headers={"Authorization": f"Bearer {admin_token}"}).status_code == 204
    assert client.get(f"{API_PREFIX}/orders/{order_id}", headers={"Authorization": f"Bearer {admin_token}"}).status_code == 404


def _first_establishment_ids(client, token, n=2):
    ref = client.get(f"{API_PREFIX}/reference-data", headers={"Authorization": f"Bearer {token}"}).json()
    ests = ref["establishments"]
    return [e["establishment_id"] for e in ests[:n]]


def test_admin_assigns_establishment_roles_and_they_reach_user(client, integration_db_session, integration_user, integration_admin):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_admin.user_password = hash_password("AdminPass123")
    integration_db_session.commit()
    admin_token = login(client, "admin", "AdminPass123")["token"]
    est = _first_establishment_ids(client, admin_token, 2)

    # админ назначает роли обычному пользователю
    resp = client.put(
        f"{API_PREFIX}/users/{integration_user.user_id}/establishment-roles",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"roles": [{"establishment_id": est[0], "role": "editor"}, {"establishment_id": est[1], "role": "viewer"}]},
    )
    assert resp.status_code == 200
    roles = {r["establishment_id"]: r["role"] for r in resp.json()["item"]["user_establishment_roles"]}
    assert roles == {est[0]: "editor", est[1]: "viewer"}

    # роли доходят до самого пользователя при логине
    login_payload = login(client, "worker", "WorkerPass123")
    user_roles = {r["establishment_id"]: r["role"] for r in login_payload["user"]["user_establishment_roles"]}
    assert user_roles == {est[0]: "editor", est[1]: "viewer"}


def test_set_establishment_roles_replaces_previous(client, integration_db_session, integration_user, integration_admin):
    integration_admin.user_password = hash_password("AdminPass123")
    integration_db_session.commit()
    admin_token = login(client, "admin", "AdminPass123")["token"]
    est = _first_establishment_ids(client, admin_token, 2)
    uid = integration_user.user_id

    client.put(f"{API_PREFIX}/users/{uid}/establishment-roles", headers={"Authorization": f"Bearer {admin_token}"},
               json={"roles": [{"establishment_id": est[0], "role": "viewer"}]})
    resp = client.put(f"{API_PREFIX}/users/{uid}/establishment-roles", headers={"Authorization": f"Bearer {admin_token}"},
                      json={"roles": [{"establishment_id": est[1], "role": "manager"}]})
    roles = {r["establishment_id"]: r["role"] for r in resp.json()["item"]["user_establishment_roles"]}
    assert roles == {est[1]: "manager"}  # прежняя роль на est[0] снята


def test_non_admin_cannot_assign_establishment_roles(client, integration_db_session, integration_user, integration_admin):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()
    worker_token = login(client, "worker", "WorkerPass123")["token"]
    est = _first_establishment_ids(client, worker_token, 1)
    resp = client.put(
        f"{API_PREFIX}/users/{integration_user.user_id}/establishment-roles",
        headers={"Authorization": f"Bearer {worker_token}"},
        json={"roles": [{"establishment_id": est[0], "role": "editor"}]},
    )
    assert resp.status_code == 403


def test_admin_can_delete_other_users_chat_message(client, integration_db_session, integration_user, integration_admin):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_admin.user_password = hash_password("AdminPass123")
    integration_db_session.commit()
    worker_token = login(client, "worker", "WorkerPass123")["token"]
    admin_token = login(client, "admin", "AdminPass123")["token"]

    mid = client.post(f"{API_PREFIX}/messages", headers={"Authorization": f"Bearer {worker_token}"},
                      json={"message_type": "message", "message_text": "чужое сообщение"}).json()["item"]["message_id"]

    # админ удаляет чужое сообщение → 204
    assert client.delete(f"{API_PREFIX}/messages/{mid}", headers={"Authorization": f"Bearer {admin_token}"}).status_code == 204


def test_non_admin_cannot_delete_other_users_message(client, integration_db_session, integration_user, integration_admin):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_admin.user_password = hash_password("AdminPass123")
    integration_db_session.commit()
    worker_token = login(client, "worker", "WorkerPass123")["token"]
    admin_token = login(client, "admin", "AdminPass123")["token"]

    # сообщение от админа, обычный пользователь пытается удалить → 403
    mid = client.post(f"{API_PREFIX}/messages", headers={"Authorization": f"Bearer {admin_token}"},
                      json={"message_type": "message", "message_text": "сообщение админа"}).json()["item"]["message_id"]
    assert client.delete(f"{API_PREFIX}/messages/{mid}", headers={"Authorization": f"Bearer {worker_token}"}).status_code == 403


def test_orders_list_scoped_to_accessible_establishments(client, integration_db_session, integration_user, integration_admin):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_admin.user_password = hash_password("AdminPass123")
    integration_db_session.commit()
    admin_token = login(client, "admin", "AdminPass123")["token"]
    worker_token = login(client, "worker", "WorkerPass123")["token"]
    est = _first_establishment_ids(client, admin_token, 2)
    ref = client.get(f"{API_PREFIX}/reference-data", headers={"Authorization": f"Bearer {admin_token}"}).json()
    method_id = ref["order_methods"][0]["order_method_id"]

    def make_order(token, establishment_id, customer):
        return client.post(f"{API_PREFIX}/orders", headers={"Authorization": f"Bearer {token}"},
            json={"order_establishment_id": establishment_id, "order_method_id": method_id, "order_customer": customer, "order_info": "x",
                  "items": [{"product_article": "SC-1", "product_name": "P", "order_item_quantity": 1, "order_item_price": "5.00"}]}).json()["item"]["order_id"]

    # админ создаёт заказы на обоих складах
    o_est0 = make_order(admin_token, est[0], "на складе 0")
    o_est1 = make_order(admin_token, est[1], "на складе 1")

    # без ролей worker видит только свои (пусто из админских)
    seen = client.get(f"{API_PREFIX}/orders?page=1&page_size=100", headers={"Authorization": f"Bearer {worker_token}"}).json()["items"]
    assert all(o["order_id"] not in (o_est0, o_est1) for o in seen)

    # даём worker роль только на est[0]
    client.put(f"{API_PREFIX}/users/{integration_user.user_id}/establishment-roles", headers={"Authorization": f"Bearer {admin_token}"},
               json={"roles": [{"establishment_id": est[0], "role": "viewer"}]})

    ids = {o["order_id"] for o in client.get(f"{API_PREFIX}/orders?page=1&page_size=100", headers={"Authorization": f"Bearer {worker_token}"}).json()["items"]}
    assert o_est0 in ids           # склад доступен — виден
    assert o_est1 not in ids       # склад недоступен — скрыт

    # даже свой заказ на НЕдоступном складе скрыт из списка (строго по складу —
    # пользователь работает в рамках своих точек).
    own_on_est1 = make_order(worker_token, est[1], "мой на складе 1")
    ids2 = {o["order_id"] for o in client.get(f"{API_PREFIX}/orders?page=1&page_size=100", headers={"Authorization": f"Bearer {worker_token}"}).json()["items"]}
    assert own_on_est1 not in ids2  # свой заказ на недоступном складе — скрыт
    assert o_est0 in ids2           # доступный склад — по-прежнему виден
    assert o_est1 not in ids2       # чужой на недоступном складе — скрыт

    # админ видит все
    admin_ids = {o["order_id"] for o in client.get(f"{API_PREFIX}/orders?page=1&page_size=100", headers={"Authorization": f"Bearer {admin_token}"}).json()["items"]}
    assert {o_est0, o_est1, own_on_est1}.issubset(admin_ids)
