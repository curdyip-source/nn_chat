from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from app.core.config import REFRESH_TOKEN_GRACE_SECONDS
from app.models.user_sessions import UserSession


class SessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, token: str, user_id: int, expires_at: datetime) -> UserSession:
        session = UserSession(
            session_token=token,
            session_user_id=user_id,
            session_expires_at=expires_at,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_active_by_token(self, token: str) -> UserSession | None:
        session = (
            self.db.query(UserSession)
            .options(joinedload(UserSession.user))
            .filter(UserSession.session_token == token)
            .first()
        )
        if session is None:
            return None
        if session.session_expires_at <= datetime.utcnow():
            self.db.delete(session)
            self.db.commit()
            return None
        return session

    def get_for_refresh(self, token: str) -> tuple[UserSession, bool] | None:
        """Resolve a refresh token, accepting the just-rotated previous token within its grace window.

        Returns ``(session, via_prev)`` where ``via_prev`` is True when the token matched the
        previous (graced) token rather than the current one, or ``None`` if no live session matches.
        """
        now = datetime.utcnow()

        session = (
            self.db.query(UserSession)
            .options(joinedload(UserSession.user))
            .filter(UserSession.session_token == token)
            .first()
        )
        if session is not None:
            if session.session_expires_at <= now:
                self.db.delete(session)
                self.db.commit()
                return None
            return session, False

        session = (
            self.db.query(UserSession)
            .options(joinedload(UserSession.user))
            .filter(UserSession.session_prev_token == token)
            .first()
        )
        if session is None:
            return None
        if session.session_expires_at <= now:
            self.db.delete(session)
            self.db.commit()
            return None
        if session.session_prev_token_expires_at is None or session.session_prev_token_expires_at <= now:
            return None
        return session, True

    def get_active_by_id(self, session_id: int) -> UserSession | None:
        session = (
            self.db.query(UserSession)
            .options(joinedload(UserSession.user))
            .filter(UserSession.session_id == session_id)
            .first()
        )
        if session is None:
            return None
        if session.session_expires_at <= datetime.utcnow():
            self.db.delete(session)
            self.db.commit()
            return None
        return session

    def list_active_for_user(self, user_id: int) -> list[UserSession]:
        sessions = (
            self.db.query(UserSession)
            .filter(UserSession.session_user_id == user_id)
            .order_by(UserSession.session_created_at.desc(), UserSession.session_id.desc())
            .all()
        )

        active_sessions: list[UserSession] = []
        expired_session_ids: list[int] = []
        now = datetime.utcnow()
        for session in sessions:
            if session.session_expires_at <= now:
                expired_session_ids.append(session.session_id)
                continue
            active_sessions.append(session)

        if expired_session_ids:
            self.db.query(UserSession).filter(UserSession.session_id.in_(expired_session_ids)).delete(synchronize_session=False)
            self.db.commit()

        return active_sessions

    def rotate_token(self, session: UserSession, *, token: str, expires_at: datetime) -> UserSession:
        if REFRESH_TOKEN_GRACE_SECONDS > 0:
            session.session_prev_token = session.session_token
            session.session_prev_token_expires_at = datetime.utcnow() + timedelta(seconds=REFRESH_TOKEN_GRACE_SECONDS)
        else:
            session.session_prev_token = None
            session.session_prev_token_expires_at = None
        session.session_token = token
        session.session_expires_at = expires_at
        self.db.commit()
        self.db.refresh(session)
        return session

    def delete_by_id(self, session_id: int) -> None:
        self.db.query(UserSession).filter(UserSession.session_id == session_id).delete(synchronize_session=False)
        self.db.commit()

    def delete_for_user(self, user_id: int) -> None:
        self.db.query(UserSession).filter(UserSession.session_user_id == user_id).delete(synchronize_session=False)
        self.db.commit()

    def delete_all_for_user(self, user_id: int) -> int:
        count = self.count_for_user(user_id)
        self.delete_for_user(user_id)
        return count

    def count_for_user(self, user_id: int) -> int:
        return self.db.query(UserSession).filter(UserSession.session_user_id == user_id).count()