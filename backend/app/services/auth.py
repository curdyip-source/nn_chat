import logging

from sqlalchemy.orm import Session

from fastapi import HTTPException, status

from app.core.audit_types import (
    ENTITY_TYPE_AUTH,
    ENTITY_TYPE_SESSION,
    EVENT_TYPE_AUTH_LOGIN_FAILED,
    EVENT_TYPE_AUTH_LOGIN_SUCCEEDED,
    EVENT_TYPE_AUTH_LOGOUT_ALL,
    EVENT_TYPE_AUTH_LOGOUT_CURRENT,
    EVENT_TYPE_AUTH_REFRESH_SUCCEEDED,
)
from app.core.security import verify_password
from app.core.session import generate_session_token, get_session_expires_at
from app.core.tokens import create_access_token
from app.repositories.sessions import SessionRepository
from app.schemas.auth import LoginPayload, RefreshTokenPayload, RegisterPayload
from app.services.audit import log_audit_event
from app.services.serializers import serialize_datetime, serialize_user, serialize_user_session
from app.services.users import get_user_by_login, register_user as register_user_service


logger = logging.getLogger("app.auth")


def _build_auth_response(user_row, refresh_session) -> dict:
    access_token, access_expires_at = create_access_token(
        session_id=refresh_session.session_id,
        user_id=user_row.user_id,
    )
    return {
        "token": access_token,
        "access_token": access_token,
        "access_expires_at": serialize_datetime(access_expires_at),
        "refresh_token": refresh_session.session_token,
        "refresh_expires_at": serialize_datetime(refresh_session.session_expires_at),
        "user": serialize_user(user_row),
    }


def login_user(db: Session, payload: LoginPayload) -> dict:
    user_row = get_user_by_login(db, payload.user_login)
    if user_row is None or not verify_password(payload.user_password, user_row.user_password):
        logger.warning(
            "auth.login.failed",
            extra={"event_type": "auth.login.failed", "auth_login": payload.user_login},
        )
        log_audit_event(
            db,
            actor_user_id=user_row.user_id if user_row is not None else None,
            entity_type=ENTITY_TYPE_AUTH,
            entity_id=user_row.user_id if user_row is not None else None,
            event_type=EVENT_TYPE_AUTH_LOGIN_FAILED,
            event_payload={"user_login": payload.user_login},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")

    if not user_row.user_active:
        logger.warning(
            "auth.login.inactive_user",
            extra={"event_type": "auth.login.inactive_user", "auth_login": payload.user_login},
        )
        log_audit_event(
            db,
            actor_user_id=user_row.user_id,
            entity_type=ENTITY_TYPE_AUTH,
            entity_id=user_row.user_id,
            event_type=EVENT_TYPE_AUTH_LOGIN_FAILED,
            event_payload={"user_login": payload.user_login, "reason": "user_inactive"},
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь деактивирован")

    refresh_token = generate_session_token()
    refresh_expires_at = get_session_expires_at()
    refresh_session = SessionRepository(db).create(
        token=refresh_token,
        user_id=user_row.user_id,
        expires_at=refresh_expires_at,
    )
    logger.info(
        "auth.login.succeeded",
        extra={
            "event_type": "auth.login.succeeded",
            "auth_login": user_row.user_login,
            "user_id": user_row.user_id,
            "session_id": refresh_session.session_id,
        },
    )
    log_audit_event(
        db,
        actor_user_id=user_row.user_id,
        entity_type=ENTITY_TYPE_SESSION,
        entity_id=refresh_session.session_id,
        event_type=EVENT_TYPE_AUTH_LOGIN_SUCCEEDED,
        event_payload={"user_id": user_row.user_id},
    )
    return _build_auth_response(user_row, refresh_session)


def register_user(db: Session, payload: RegisterPayload) -> dict:
    return register_user_service(db, payload)


def logout_user(db: Session, current_user: dict, session_id: int) -> dict:
    SessionRepository(db).delete_by_id(session_id)
    logger.info(
        "auth.logout.current",
        extra={
            "event_type": "auth.logout.current",
            "user_id": current_user["user_id"],
            "session_id": session_id,
        },
    )
    log_audit_event(
        db,
        actor_user_id=current_user["user_id"],
        entity_type=ENTITY_TYPE_SESSION,
        entity_id=session_id,
        event_type=EVENT_TYPE_AUTH_LOGOUT_CURRENT,
        event_payload={"user_id": current_user["user_id"]},
    )
    return {"message": "Сессия завершена"}


def refresh_user_token(db: Session, payload: RefreshTokenPayload) -> dict:
    repository = SessionRepository(db)
    refresh_session = repository.get_active_by_token(payload.refresh_token)
    if refresh_session is None:
        logger.warning("auth.refresh.failed", extra={"event_type": "auth.refresh.failed"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token не найден или истек")
    if not refresh_session.user.user_active:
        repository.delete_by_id(refresh_session.session_id)
        logger.warning(
            "auth.refresh.inactive_user",
            extra={
                "event_type": "auth.refresh.inactive_user",
                "user_id": refresh_session.session_user_id,
                "session_id": refresh_session.session_id,
            },
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь деактивирован")

    rotated_token = generate_session_token()
    refresh_expires_at = get_session_expires_at()
    refresh_session = repository.rotate_token(refresh_session, token=rotated_token, expires_at=refresh_expires_at)
    logger.info(
        "auth.refresh.succeeded",
        extra={
            "event_type": "auth.refresh.succeeded",
            "user_id": refresh_session.session_user_id,
            "session_id": refresh_session.session_id,
        },
    )
    log_audit_event(
        db,
        actor_user_id=refresh_session.session_user_id,
        entity_type=ENTITY_TYPE_SESSION,
        entity_id=refresh_session.session_id,
        event_type=EVENT_TYPE_AUTH_REFRESH_SUCCEEDED,
        event_payload={"user_id": refresh_session.session_user_id},
    )
    return _build_auth_response(refresh_session.user, refresh_session)


def list_user_sessions(db: Session, current_user: dict, current_session_id: int) -> list[dict]:
    sessions = SessionRepository(db).list_active_for_user(current_user["user_id"])
    return [serialize_user_session(session, is_current=session.session_id == current_session_id) for session in sessions]


def logout_all_devices(db: Session, current_user: dict) -> dict:
    deleted_count = SessionRepository(db).delete_all_for_user(current_user["user_id"])
    logger.info(
        "auth.logout.all",
        extra={"event_type": "auth.logout.all", "user_id": current_user["user_id"]},
    )
    log_audit_event(
        db,
        actor_user_id=current_user["user_id"],
        entity_type=ENTITY_TYPE_SESSION,
        entity_id=None,
        event_type=EVENT_TYPE_AUTH_LOGOUT_ALL,
        event_payload={"deleted_sessions": deleted_count},
    )
    return {"message": "Все устройства разлогинены", "deleted_sessions": deleted_count}