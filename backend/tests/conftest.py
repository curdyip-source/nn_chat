from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models import User


def _make_sqlite_unicode_aware(engine) -> None:
    # Встроенный SQLite lower() работает только с ASCII; в проде (PostgreSQL)
    # lower() — Unicode-aware. Регистрируем питоновский lower(), чтобы тесты
    # отражали продовое поведение для кириллицы.
    @event.listens_for(engine, "connect")
    def _register(dbapi_connection, _record):  # noqa: ANN001
        dbapi_connection.create_function("lower", 1, lambda v: v.lower() if isinstance(v, str) else v)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _make_sqlite_unicode_aware(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def integration_db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'integration-test.db'}"


@pytest.fixture()
def integration_db_session(integration_db_url: str) -> Generator[Session, None, None]:
    engine = create_engine(
        integration_db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _make_sqlite_unicode_aware(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(integration_db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield integration_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def existing_admin(db_session: Session) -> User:
    admin = User(
        user_login="admin",
        user_password="hashed-password",
        user_admin=True,
        user_active=True,
        user_first_name="Admin",
        user_second_name="User",
        user_age=35,
        user_address="Admin Street",
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture()
def existing_user(db_session: Session) -> User:
    user = User(
        user_login="worker",
        user_password="hashed-password",
        user_admin=False,
        user_active=True,
        user_first_name="Worker",
        user_second_name="User",
        user_age=25,
        user_address="Worker Street",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def integration_admin(integration_db_session: Session) -> User:
    admin = User(
        user_login="admin",
        user_password="hashed-password",
        user_admin=True,
        user_active=True,
        user_first_name="Admin",
        user_second_name="User",
        user_age=35,
        user_address="Admin Street",
    )
    integration_db_session.add(admin)
    integration_db_session.commit()
    integration_db_session.refresh(admin)
    return admin


@pytest.fixture()
def integration_user(integration_db_session: Session) -> User:
    user = User(
        user_login="worker",
        user_password="hashed-password",
        user_admin=False,
        user_active=True,
        user_first_name="Worker",
        user_second_name="User",
        user_age=25,
        user_address="Worker Street",
        # Полный профиль прав (view/edit/delete=all, создание) — чтобы функциональные
        # тесты работали без настройки складов. Тесты про сами права задают профиль явно.
        user_view_scope="all",
        user_can_create=True,
        user_edit_scope="all",
        user_delete_scope="all",
    )
    integration_db_session.add(user)
    integration_db_session.commit()
    integration_db_session.refresh(user)
    return user