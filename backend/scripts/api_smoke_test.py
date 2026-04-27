import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request
import uuid

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import SessionLocal
from app.models.users import User

API_URL = os.getenv("SMOKE_TEST_API_URL", "http://127.0.0.1:8000")
API_PREFIX = os.getenv("SMOKE_TEST_API_PREFIX", "/api/v1")
ADMIN_LOGIN = os.getenv("SMOKE_TEST_ADMIN_LOGIN", "").strip()
ADMIN_PASSWORD = os.getenv("SMOKE_TEST_ADMIN_PASSWORD", "").strip()
USER_PASSWORD = "SmokeUserPass123!"
SMOKE_PREFIX = "smoke_user_"


def log(message: str) -> None:
    print(message, flush=True)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def request_json(method: str, path: str, payload: dict | None = None, token: str | None = None, expected_status: int | tuple[int, ...] = 200) -> dict:
    url = f"{API_URL}{API_PREFIX}{path}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status_code = response.getcode()
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        status_code = error.code
        response_body = error.read().decode("utf-8")

    allowed_statuses = expected_status if isinstance(expected_status, tuple) else (expected_status,)
    if status_code not in allowed_statuses:
        raise AssertionError(f"{method} {path} returned {status_code}, expected {allowed_statuses}. Body: {response_body}")

    return json.loads(response_body) if response_body else {}


def cleanup_smoke_data() -> None:
    db = SessionLocal()
    try:
        smoke_users = db.query(User).filter(User.user_login.like(f"{SMOKE_PREFIX}%")).all()
        for smoke_user in smoke_users:
            db.delete(smoke_user)

        db.commit()
    finally:
        db.close()


def wait_for_backend() -> None:
    last_error = None
    for _ in range(20):
        try:
            urllib.request.urlopen(f"{API_URL}/", timeout=20).read()
            return
        except Exception as error:
            last_error = error
            time.sleep(1)
    raise RuntimeError(f"Backend is not ready: {last_error}")


def run() -> None:
    log("Preparing smoke data...")
    cleanup_smoke_data()
    wait_for_backend()

    if not ADMIN_LOGIN or not ADMIN_PASSWORD:
        log("Skipping authenticated deep smoke because SMOKE_TEST_ADMIN_LOGIN and SMOKE_TEST_ADMIN_PASSWORD are not configured.")
        return

    unique_suffix = uuid.uuid4().hex[:8]
    smoke_user_login = f"{SMOKE_PREFIX}{unique_suffix}"

    log("Checking unauthorized access...")
    request_json("POST", "/users", payload={"user_login": "forbidden", "user_password": "ignored123", "user_first_name": "A", "user_second_name": "B", "user_age": 20, "user_address": "Nope", "user_admin": False}, expected_status=401)

    log("Logging in as smoke admin...")
    admin_login = request_json("POST", "/auth/login", payload={"user_login": ADMIN_LOGIN, "user_password": ADMIN_PASSWORD}, expected_status=200)
    admin_token = admin_login["token"]
    admin_refresh_token = admin_login["refresh_token"]
    admin_user = request_json("GET", "/auth/me", token=admin_token, expected_status=200)["user"]
    assert_true(admin_user["user_admin"] is True, "Smoke admin must have admin rights")

    log("Refreshing admin access token...")
    refreshed_admin = request_json(
        "POST",
        "/auth/refresh",
        payload={"refresh_token": admin_refresh_token},
        expected_status=200,
    )
    admin_token = refreshed_admin["token"]

    log("Checking active sessions list...")
    sessions = request_json("GET", "/auth/sessions", token=admin_token, expected_status=200)["items"]
    assert_true(any(item["is_current"] is True for item in sessions), "Current admin session must be marked as current")

    log("Creating regular user via API...")
    created_user = request_json(
        "POST",
        "/users",
        token=admin_token,
        payload={
            "user_login": smoke_user_login,
            "user_password": USER_PASSWORD,
            "user_first_name": "Smoke",
            "user_second_name": "User",
            "user_age": 22,
            "user_address": "Smoke Street",
            "user_admin": False,
            "user_active": True,
        },
        expected_status=201,
    )["item"]

    log("Checking user listing as admin...")
    users_response = request_json("GET", "/users?search=smoke_user&page=1&page_size=10", token=admin_token, expected_status=200)
    users = users_response["items"]
    assert_true(any(item["user_login"] == smoke_user_login for item in users), "Created smoke user is missing in /users")

    log("Logging in as regular user...")
    user_login = request_json("POST", "/auth/login", payload={"user_login": smoke_user_login, "user_password": USER_PASSWORD}, expected_status=200)
    user_token = user_login["token"]

    log("Checking admin-only access denial...")
    request_json("GET", "/users", token=user_token, expected_status=403)

    log("Creating document metadata as regular user...")
    created_document = request_json(
        "POST",
        "/documents",
        token=user_token,
        payload={
            "document_kind": "passport",
            "document_original_filename": "passport.jpg",
            "document_mime_type": "image/jpeg",
            "document_storage_key": f"smoke/passport-{unique_suffix}.jpg",
            "document_note": "Smoke passport",
            "document_size_bytes": 2048,
        },
        expected_status=201,
    )["item"]

    log("Checking document metadata listing with filters...")
    documents = request_json(
        "GET",
        "/documents?document_kind=passport&document_status=pending&page=1&page_size=10",
        token=user_token,
        expected_status=200,
    )["items"]
    assert_true(any(item["document_id"] == created_document["document_id"] for item in documents), "Created document metadata is missing in /documents")

    log("Verifying document metadata as admin...")
    updated_document = request_json(
        "PUT",
        f"/documents/{created_document['document_id']}",
        token=admin_token,
        payload={
            "document_status": "verified",
            "document_note": "Checked by smoke admin",
        },
        expected_status=200,
    )["item"]
    assert_true(updated_document["document_status"] == "verified", "Document status should become verified")

    log("Checking audit trail as admin...")
    audit_events = request_json(
        "GET",
        f"/audit-events?entity_type=document&entity_id={created_document['document_id']}&event_type=document.create&page=1&page_size=10",
        token=admin_token,
        expected_status=200,
    )["items"]
    assert_true(any(item["entity_id"] == created_document["document_id"] for item in audit_events), "Document audit event is missing in /audit-events")

    log("Logging out regular user...")
    request_json("POST", "/auth/logout", token=user_token, expected_status=200)

    log("Deleting regular user as admin...")
    request_json("DELETE", f"/users/{created_user['user_id']}", token=admin_token, expected_status=200)

    log("Logging out admin...")
    request_json("POST", "/auth/logout", token=admin_token, expected_status=200)

    log("Smoke test passed: auth, users, documents, audit.")


if __name__ == "__main__":
    try:
        run()
    except Exception as error:
        log(f"Smoke test failed: {error}")
        sys.exit(1)