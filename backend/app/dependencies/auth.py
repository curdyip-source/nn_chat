from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.request_context import set_current_user_id
from app.core.tokens import decode_access_token
from app.models.user_sessions import UserSession
from app.repositories.sessions import SessionRepository
from app.services.users import get_user_by_id_or_401


def get_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется авторизация")

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный формат токена")

    token = authorization[len(prefix):].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пустой токен")

    return token


def get_current_user(request: Request, authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> dict:
    session = get_current_session(authorization, db)

    try:
        user = get_user_by_id_or_401(db, session.session_user_id)
        set_current_user_id(user["user_id"])
        request.state.user_id = user["user_id"]
        return user
    except HTTPException:
        SessionRepository(db).delete_by_id(session.session_id)
        raise


def get_current_session(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> UserSession:
    token = get_bearer_token(authorization)
    payload = decode_access_token(token)
    session = SessionRepository(db).get_active_by_id(payload["session_id"])
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия не найдена")
    if session.session_user_id != payload["user_id"]:
        SessionRepository(db).delete_by_id(session.session_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия не соответствует токену")
    return session


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if not user["user_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нужны права администратора")
    return user