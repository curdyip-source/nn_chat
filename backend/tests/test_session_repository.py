from datetime import datetime, timedelta

from app.repositories.sessions import SessionRepository


def test_session_repository_creates_and_loads_active_session(db_session, existing_user):
    repository = SessionRepository(db_session)

    created = repository.create(
        token="test-token",
        user_id=existing_user.user_id,
        expires_at=datetime.utcnow() + timedelta(days=1),
    )
    loaded = repository.get_active_by_token("test-token")

    assert created.session_id is not None
    assert loaded is not None
    assert loaded.user.user_login == existing_user.user_login


def test_session_repository_deletes_expired_session(db_session, existing_user):
    repository = SessionRepository(db_session)

    repository.create(
        token="expired-token",
        user_id=existing_user.user_id,
        expires_at=datetime.utcnow() - timedelta(minutes=1),
    )

    assert repository.get_active_by_token("expired-token") is None


def test_session_repository_rotates_refresh_token(db_session, existing_user):
    repository = SessionRepository(db_session)

    session = repository.create(
        token="old-token",
        user_id=existing_user.user_id,
        expires_at=datetime.utcnow() + timedelta(days=1),
    )
    repository.rotate_token(
        session,
        token="new-token",
        expires_at=datetime.utcnow() + timedelta(days=2),
    )

    assert repository.get_active_by_token("old-token") is None
    assert repository.get_active_by_token("new-token") is not None


def test_session_repository_lists_only_active_sessions(db_session, existing_user):
    repository = SessionRepository(db_session)

    repository.create(
        token="active-token",
        user_id=existing_user.user_id,
        expires_at=datetime.utcnow() + timedelta(days=1),
    )
    repository.create(
        token="expired-token-2",
        user_id=existing_user.user_id,
        expires_at=datetime.utcnow() - timedelta(minutes=1),
    )

    sessions = repository.list_active_for_user(existing_user.user_id)

    assert len(sessions) == 1
    assert sessions[0].session_token == "active-token"