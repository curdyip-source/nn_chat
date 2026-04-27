from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.users import SQL_ID_TYPE


class ProfilePhoto(Base):
    __tablename__ = "profile_photos"

    profile_photo_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True, index=True)
    profile_photo_mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    profile_photo_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    profile_photo_updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profile_photo_asset")