import secrets
from datetime import datetime, timedelta

from app.core.config import REFRESH_TOKEN_TTL_DAYS


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def get_session_expires_at() -> datetime:
    return datetime.utcnow() + timedelta(days=REFRESH_TOKEN_TTL_DAYS)