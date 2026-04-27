from datetime import datetime

from app.core.audit_types import EVENT_TYPE_DOCUMENT_CREATE
from app.core.config import FIRST_ADMIN_PASS
from app.core.security import hash_password
from app.models import AuditEvent, User


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


def test_bootstrap_and_auth_me_flow(client):
    bootstrap_response = client.post(
        f"{API_PREFIX}/users/bootstrap",
        json={
            "first_admin_pass": FIRST_ADMIN_PASS,
            "user_login": "first_admin",
            "user_password": "StrongPass123",
            "user_admin": False,
            "user_first_name": "First",
            "user_second_name": "Admin",
            "user_age": 30,
            "user_address": "Bootstrap Street",
        },
    )

    assert bootstrap_response.status_code == 201
    bootstrap_payload = bootstrap_response.json()
    assert bootstrap_payload["user"]["user_admin"] is True
    assert bootstrap_payload["user"]["user_active"] is True
    assert bootstrap_payload["user"]["user_created_at"]
    assert bootstrap_payload["refresh_token"]

    me_response = client.get(
        f"{API_PREFIX}/auth/me",
        headers={"Authorization": f"Bearer {bootstrap_payload['token']}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["user"]["user_login"] == "first_admin"


def test_bootstrap_rejects_invalid_admin_key(client):
    response = client.post(
        f"{API_PREFIX}/users/bootstrap",
        json={
            "first_admin_pass": "wrong-admin-key",
            "user_login": "first_admin",
            "user_password": "StrongPass123",
            "user_admin": False,
            "user_first_name": "First",
            "user_second_name": "Admin",
            "user_age": 30,
            "user_address": "Bootstrap Street",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "Неверный ключ первого администратора"


def test_health_endpoints_are_available(client):
    live_response = client.get(f"{API_PREFIX}/health/live")
    assert live_response.status_code == 200
    assert live_response.json() == {"status": "ok"}

    ready_response = client.get(f"{API_PREFIX}/health/ready")
    assert ready_response.status_code == 200
    assert ready_response.json() == {"status": "ok", "database": "ok"}


def test_admin_can_create_user_and_regular_user_is_forbidden(client, integration_db_session, integration_admin):
    integration_admin.user_password = hash_password("AdminPass123")
    integration_db_session.commit()

    admin_auth = login(client, "admin", "AdminPass123")
    admin_token = admin_auth["token"]

    create_response = client.post(
        f"{API_PREFIX}/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "user_login": "created_user",
            "user_password": "UserPass123",
            "user_admin": False,
            "user_active": True,
            "user_first_name": "Created",
            "user_second_name": "User",
            "user_age": 24,
            "user_address": "Created Street",
        },
    )

    assert create_response.status_code == 201
    assert create_response.json()["item"]["user_login"] == "created_user"
    assert create_response.json()["item"]["user_active"] is True
    assert create_response.json()["item"]["user_created_at"]

    created_user = integration_db_session.query(User).filter(User.user_login == "created_user").one()
    created_user.user_password = hash_password("UserPass123")
    integration_db_session.commit()

    user_token = login(client, "created_user", "UserPass123")["token"]
    forbidden_response = client.get(
        f"{API_PREFIX}/users",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert forbidden_response.status_code == 403
    assert forbidden_response.json()["error"]["code"] == "http_error"


def test_admin_can_manage_documents_created_by_user(client, integration_db_session, integration_admin, integration_user):
    integration_admin.user_password = hash_password("AdminPass123")
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()

    admin_token = login(client, "admin", "AdminPass123")["token"]
    user_token = login(client, "worker", "WorkerPass123")["token"]

    create_response = client.post(
        f"{API_PREFIX}/documents",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "document_kind": "passport",
            "document_original_filename": "integration-passport.jpg",
            "document_mime_type": "image/jpeg",
            "document_storage_key": "documents/integration-passport.jpg",
            "document_note": "uploaded by worker",
            "document_size_bytes": 1024,
        },
    )

    assert create_response.status_code == 201
    document_id = create_response.json()["item"]["document_id"]

    update_response = client.put(
        f"{API_PREFIX}/documents/{document_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "document_status": "verified",
            "document_note": "verified by admin",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["item"]["document_status"] == "verified"

    forbidden_response = client.put(
        f"{API_PREFIX}/documents/{document_id}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"document_status": "rejected"},
    )

    assert forbidden_response.status_code == 403


def test_refresh_endpoint_rotates_refresh_token_and_returns_new_access_token(client, integration_db_session, integration_user):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()

    auth_payload = login(client, "worker", "WorkerPass123")
    refreshed = client.post(
        f"{API_PREFIX}/auth/refresh",
        json={"refresh_token": auth_payload["refresh_token"]},
    )

    assert refreshed.status_code == 200
    refreshed_payload = refreshed.json()
    assert refreshed_payload["refresh_token"] != auth_payload["refresh_token"]

    me_response = client.get(
        f"{API_PREFIX}/auth/me",
        headers={"Authorization": f"Bearer {refreshed_payload['token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["user"]["user_login"] == "worker"


def test_inactive_user_cannot_login(client, integration_db_session, integration_admin):
    integration_admin.user_password = hash_password("AdminPass123")
    integration_db_session.commit()

    admin_token = login(client, "admin", "AdminPass123")["token"]
    create_response = client.post(
        f"{API_PREFIX}/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "user_login": "blocked_user",
            "user_password": "BlockedPass123",
            "user_admin": False,
            "user_active": False,
            "user_first_name": "Blocked",
            "user_second_name": "User",
            "user_age": 26,
            "user_address": "Blocked Street",
        },
    )
    assert create_response.status_code == 201

    login_response = client.post(
        f"{API_PREFIX}/auth/login",
        json={
            "user_login": "blocked_user",
            "user_password": "BlockedPass123",
        },
    )

    assert login_response.status_code == 403
    assert login_response.json()["error"]["message"] == "Пользователь деактивирован"


def test_public_registration_creates_inactive_user(client, integration_db_session):
    response = client.post(
        f"{API_PREFIX}/auth/register",
        json={
            "user_login": "public_user",
            "user_password": "PublicPass123",
            "user_first_name": "Public",
            "user_second_name": "User",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["user_login"] == "public_user"
    assert payload["user"]["user_active"] is False
    assert payload["user"]["user_admin"] is False


def test_sessions_endpoint_and_logout_all_devices(client, integration_db_session, integration_user):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()

    first_auth = login(client, "worker", "WorkerPass123")
    second_auth = login(client, "worker", "WorkerPass123")

    sessions_response = client.get(
        f"{API_PREFIX}/auth/sessions",
        headers={"Authorization": f"Bearer {second_auth['token']}"},
    )
    assert sessions_response.status_code == 200
    sessions = sessions_response.json()["items"]
    assert len(sessions) == 2
    assert any(item["is_current"] is True for item in sessions)

    logout_all_response = client.post(
        f"{API_PREFIX}/auth/logout-all",
        headers={"Authorization": f"Bearer {second_auth['token']}"},
    )
    assert logout_all_response.status_code == 200
    assert logout_all_response.json()["deleted_sessions"] == 2

    me_after_logout = client.get(
        f"{API_PREFIX}/auth/me",
        headers={"Authorization": f"Bearer {first_auth['token']}"},
    )
    assert me_after_logout.status_code == 401


def test_documents_endpoint_supports_pagination_and_filters(client, integration_db_session, integration_user):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()

    auth_payload = login(client, "worker", "WorkerPass123")
    token = auth_payload["token"]

    client.post(
        f"{API_PREFIX}/documents",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "document_kind": "passport",
            "document_original_filename": "alpha.jpg",
            "document_mime_type": "image/jpeg",
            "document_storage_key": "documents/alpha.jpg",
            "document_note": "alpha",
            "document_size_bytes": 123,
        },
    )
    client.post(
        f"{API_PREFIX}/documents",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "document_kind": "selfie",
            "document_original_filename": "beta.jpg",
            "document_mime_type": "image/jpeg",
            "document_storage_key": "documents/beta.jpg",
            "document_note": "beta",
            "document_size_bytes": 456,
        },
    )

    response = client.get(
        f"{API_PREFIX}/documents?document_kind=selfie&document_status=pending&page=1&page_size=1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 1
    assert payload["items"][0]["document_kind"] == "selfie"


def test_users_endpoint_supports_pagination_and_filters(client, integration_db_session, integration_admin, integration_user):
    integration_admin.user_password = hash_password("AdminPass123")
    integration_db_session.commit()

    token = login(client, "admin", "AdminPass123")["token"]
    response = client.get(
        f"{API_PREFIX}/users?search=work&admin_only=false&page=1&page_size=1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 1
    assert payload["items"][0]["user_login"] == "worker"


def test_documents_metadata_flow(client, integration_db_session, integration_admin, integration_user):
    integration_admin.user_password = hash_password("AdminPass123")
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()

    user_token = login(client, "worker", "WorkerPass123")["token"]
    admin_token = login(client, "admin", "AdminPass123")["token"]

    create_response = client.post(
        f"{API_PREFIX}/documents",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "document_kind": "passport",
            "document_original_filename": "passport.jpg",
            "document_mime_type": "image/jpeg",
            "document_storage_key": "documents/passport-worker.jpg",
            "document_note": "front side",
            "document_size_bytes": 2048,
        },
    )
    assert create_response.status_code == 201
    document_id = create_response.json()["item"]["document_id"]

    list_response = client.get(
        f"{API_PREFIX}/documents?document_kind=passport&document_status=pending&page=1&page_size=10",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert list_response.status_code == 200
    assert list_response.json()["pagination"]["total"] == 1

    update_response = client.put(
        f"{API_PREFIX}/documents/{document_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"document_status": "verified", "document_note": "validated"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["item"]["document_status"] == "verified"


def test_admin_can_view_audit_events_with_filters(client, integration_db_session, integration_admin, integration_user):
    integration_admin.user_password = hash_password("AdminPass123")
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()

    admin_auth = login(client, "admin", "AdminPass123")
    admin_token = admin_auth["token"]
    user_token = login(client, "worker", "WorkerPass123")["token"]

    document_response = client.post(
        f"{API_PREFIX}/documents",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "document_kind": "passport",
            "document_original_filename": "audit.jpg",
            "document_mime_type": "image/jpeg",
            "document_storage_key": "documents/audit.jpg",
            "document_note": "audit",
            "document_size_bytes": 100,
        },
    )
    assert document_response.status_code == 201
    document_id = document_response.json()["item"]["document_id"]

    audit_response = client.get(
        f"{API_PREFIX}/audit-events?entity_type=document&entity_id={document_id}&event_type={EVENT_TYPE_DOCUMENT_CREATE}&page=1&page_size=10",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert audit_response.status_code == 200
    payload = audit_response.json()
    assert payload["pagination"]["total"] == 1
    assert payload["items"][0]["actor_user_login"] == "worker"
    assert payload["items"][0]["event_type"] == EVENT_TYPE_DOCUMENT_CREATE


def test_audit_event_includes_request_context(client, integration_db_session, integration_admin, integration_user):
    integration_admin.user_password = hash_password("AdminPass123")
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()

    admin_token = login(client, "admin", "AdminPass123")["token"]
    user_token = login(client, "worker", "WorkerPass123")["token"]

    create_response = client.post(
        f"{API_PREFIX}/documents",
        headers={
            "Authorization": f"Bearer {user_token}",
            "User-Agent": "integration-audit-test",
        },
        json={
            "document_kind": "passport",
            "document_original_filename": "context.jpg",
            "document_mime_type": "image/jpeg",
            "document_storage_key": "documents/context.jpg",
            "document_note": "context",
            "document_size_bytes": 100,
        },
    )
    assert create_response.status_code == 201
    request_id = create_response.headers["X-Request-ID"]
    document_id = create_response.json()["item"]["document_id"]

    audit_response = client.get(
        f"{API_PREFIX}/audit-events?entity_type=document&entity_id={document_id}&event_type={EVENT_TYPE_DOCUMENT_CREATE}&page=1&page_size=10",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert audit_response.status_code == 200
    audit_item = audit_response.json()["items"][0]
    assert audit_item["request_id"] == request_id
    assert audit_item["user_agent"] == "integration-audit-test"
    assert audit_item["ip_address"] == "testclient"


def test_admin_can_filter_audit_events_by_date_range(client, integration_db_session, integration_admin, integration_user):
    integration_admin.user_password = hash_password("AdminPass123")
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()

    admin_token = login(client, "admin", "AdminPass123")["token"]
    user_token = login(client, "worker", "WorkerPass123")["token"]

    create_response = client.post(
        f"{API_PREFIX}/documents",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "document_kind": "passport",
            "document_original_filename": "timed.jpg",
            "document_mime_type": "image/jpeg",
            "document_storage_key": "documents/timed.jpg",
            "document_note": "timed",
            "document_size_bytes": 100,
        },
    )
    assert create_response.status_code == 201

    audit_event = integration_db_session.query(AuditEvent).filter(AuditEvent.event_type == EVENT_TYPE_DOCUMENT_CREATE).order_by(AuditEvent.audit_event_id.desc()).first()
    assert audit_event is not None
    audit_event.created_at = datetime(2026, 3, 22, 10, 0, 0)
    integration_db_session.commit()

    included_response = client.get(
        f"{API_PREFIX}/audit-events?event_type={EVENT_TYPE_DOCUMENT_CREATE}&date_from=2026-03-22T09:00:00&date_to=2026-03-22T11:00:00",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert included_response.status_code == 200
    included_payload = included_response.json()
    assert included_payload["pagination"]["total"] >= 1
    assert any(item["audit_event_id"] == audit_event.audit_event_id for item in included_payload["items"])
    assert included_payload["filters"]["date_from"] == "2026-03-22T09:00:00"
    assert included_payload["filters"]["date_to"] == "2026-03-22T11:00:00"

    excluded_response = client.get(
        f"{API_PREFIX}/audit-events?event_type={EVENT_TYPE_DOCUMENT_CREATE}&date_from=2026-03-22T11:00:01&date_to=2026-03-22T12:00:00",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert excluded_response.status_code == 200
    excluded_payload = excluded_response.json()
    assert excluded_payload["pagination"]["total"] == 0


def test_regular_user_cannot_view_audit_events(client, integration_db_session, integration_user):
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()

    user_token = login(client, "worker", "WorkerPass123")["token"]
    response = client.get(
        f"{API_PREFIX}/audit-events",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "http_error"


def test_validation_error_uses_global_error_format(client):
    response = client.post(
        f"{API_PREFIX}/auth/login",
        json={"user_login": "ab", "user_password": "123"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["request_id"]