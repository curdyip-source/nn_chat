from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_session, get_current_user
from app.schemas.auth import LoginPayload, RefreshTokenPayload, RegisterPayload
from app.services.auth import list_user_sessions, login_user, logout_all_devices, logout_user, refresh_user_token, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginPayload, db: Session = Depends(get_db)) -> dict:
    return login_user(db, payload)


@router.post("/register")
def register(payload: RegisterPayload, db: Session = Depends(get_db)) -> dict:
    return register_user(db, payload)


@router.get("/me")
def auth_me(user: dict = Depends(get_current_user)) -> dict:
    return {"user": user}


@router.post("/refresh")
def refresh(payload: RefreshTokenPayload, db: Session = Depends(get_db)) -> dict:
    return refresh_user_token(db, payload)


@router.get("/sessions")
def sessions(user: dict = Depends(get_current_user), current_session = Depends(get_current_session), db: Session = Depends(get_db)) -> dict:
    return {"items": list_user_sessions(db, user, current_session.session_id)}


@router.post("/logout-all")
def logout_all(user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return logout_all_devices(db, user)


@router.post("/logout")
def logout(user: dict = Depends(get_current_user), current_session = Depends(get_current_session), db: Session = Depends(get_db)) -> dict:
    return logout_user(db, user, current_session.session_id)