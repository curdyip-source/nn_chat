from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

SQL_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class IdempotencyKey(Base):
    """A captured response for a client-supplied Idempotency-Key.

    Lets the API replay the original result instead of re-running a non-idempotent POST that the
    client re-sent after a lost response (flaky network / VPN drop), preventing duplicate writes.
    """

    __tablename__ = "idempotency_keys"

    idempotency_key_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    idempotency_key_value: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    idempotency_key_user_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, nullable=True, index=True)
    idempotency_key_method: Mapped[str] = mapped_column(String(10), nullable=False)
    idempotency_key_path: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key_status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key_response: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), index=True)
