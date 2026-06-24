import time
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def wait_for_database(max_attempts: int = 20, delay_seconds: int = 2) -> None:
    last_error = None
    for _ in range(max_attempts):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                return
        except Exception as error:
            last_error = error
            time.sleep(delay_seconds)

    if last_error is not None:
        raise last_error


def get_database_info() -> dict:
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT current_database(), current_user"))
            row = result.fetchone()
            return {
                "database": row[0],
                "user": row[1],
            }
    except Exception:
        return {
            "database": engine.url.database,
            "user": engine.url.username,
        }