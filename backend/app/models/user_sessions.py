from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

SQL_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class UserSession(Base):
    __tablename__ = "user_sessions"

    session_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    session_token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    # Previous token, kept briefly after rotation so an in-flight/retried refresh still resolves.
    session_prev_token: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    session_prev_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    session_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    session_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    session_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user = relationship("User", back_populates="sessions")