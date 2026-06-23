from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

SQL_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class UserDevice(Base):
    __tablename__ = "user_devices"

    user_device_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    user_device_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    user_device_token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    user_device_platform: Mapped[str] = mapped_column(String(50), nullable=False)
    user_device_environment: Mapped[str] = mapped_column(String(20), nullable=False, default="production", server_default="production")
    user_device_is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=func.true())
    user_device_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    user_device_updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="user_devices")