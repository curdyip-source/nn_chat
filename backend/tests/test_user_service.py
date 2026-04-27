import pytest
from fastapi import HTTPException

from app.schemas.auth import RegisterPayload
from app.schemas.users import UserCreatePayload
from app.services.users import UserService


def test_bootstrap_first_user_creates_admin(db_session):
    service = UserService(db_session)

    result = service.bootstrap_first_user(
        UserCreatePayload(
            user_login="first_admin",
            user_password="StrongPass123",
            user_admin=False,
            user_first_name="First",
            user_second_name="Admin",
            user_age=30,
            user_address="Bootstrap Street",
        )
    )

    assert result["user"]["user_admin"] is True
    assert result["user"]["user_active"] is True
    assert result["user"]["user_created_at"]
    assert result["token"]
    assert result["refresh_token"]


def test_create_user_allows_setting_inactive_flag(db_session, existing_admin):
    service = UserService(db_session)

    result = service.create_user(
        UserCreatePayload(
            user_login="inactive_user",
            user_password="StrongPass123",
            user_admin=False,
            user_active=False,
            user_first_name="Inactive",
            user_second_name="User",
            user_age=20,
            user_address="Inactive Street",
        ),
        {"user_id": existing_admin.user_id, "user_admin": True},
    )

    assert result["user_active"] is False
    assert result["user_created_at"]


def test_register_user_creates_inactive_non_admin_user(db_session):
    service = UserService(db_session)

    result = service.register_user(
        RegisterPayload(
            user_login="new_public_user",
            user_password="StrongPass123",
            user_first_name="New",
            user_second_name="User",
        )
    )

    assert result["user"]["user_admin"] is False
    assert result["user"]["user_active"] is False
    assert result["user"]["user_created_at"]


def test_create_user_rejects_duplicate_login(db_session, existing_admin):
    service = UserService(db_session)

    with pytest.raises(HTTPException) as error:
        service.create_user(
            UserCreatePayload(
                user_login="admin",
                user_password="StrongPass123",
                user_admin=False,
                user_first_name="Dup",
                user_second_name="User",
                user_age=20,
                user_address="Dup Street",
            ),
            {"user_id": existing_admin.user_id, "user_admin": True},
        )

    assert error.value.status_code == 409


def test_delete_user_rejects_last_admin(db_session, existing_admin):
    service = UserService(db_session)

    with pytest.raises(HTTPException) as error:
        service.delete_user(existing_admin.user_id, {"user_id": 999, "user_admin": True})

    assert error.value.status_code == 400