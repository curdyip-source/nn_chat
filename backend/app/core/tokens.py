import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta

from fastapi import HTTPException, status

from app.core.config import ACCESS_TOKEN_TTL_MINUTES, AUTH_TOKEN_SECRET


def _encode_json(data: dict) -> str:
    raw = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _decode_json(value: str) -> dict:
    padding = "=" * (-len(value) % 4)
    raw = base64.urlsafe_b64decode((value + padding).encode("utf-8"))
    return json.loads(raw.decode("utf-8"))


def _sign(data: str) -> str:
    digest = hmac.new(AUTH_TOKEN_SECRET.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def create_access_token(*, session_id: int, user_id: int) -> tuple[str, datetime]:
    expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES)
    payload = {
        "type": "access",
        "session_id": session_id,
        "user_id": user_id,
        "exp": int(expires_at.timestamp()),
    }
    encoded_payload = _encode_json(payload)
    signature = _sign(encoded_payload)
    return f"{encoded_payload}.{signature}", expires_at


def decode_access_token(token: str) -> dict:
    try:
        encoded_payload, signature = token.split(".", 1)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный access token") from error

    expected_signature = _sign(encoded_payload)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверная подпись access token")

    try:
        payload = _decode_json(encoded_payload)
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Невалидный payload access token") from error

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный тип токена")
    if payload.get("exp", 0) <= int(datetime.utcnow().timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token истек")
    return payload