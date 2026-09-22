from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

SQL_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class SystemMessage(Base):
    """Системное сообщение из «Админки» — блокирующий оверлей в приложении, пока
    получатель явно не подтвердит прочтение («важное» просит подтвердить дважды —
    это чисто клиентский шаг, на сервер уходит одно финальное подтверждение).
    Получатели — снимок адресатов на момент отправки (system_message_recipients),
    а не «все, кто есть в системе сейчас» — так список читателей не размывается
    новыми пользователями, заведёнными уже после рассылки."""

    __tablename__ = "system_messages"

    system_message_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    system_message_text: Mapped[str] = mapped_column(Text, nullable=False)
    system_message_important: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    system_message_created_by_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    system_message_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    created_by = relationship("User", foreign_keys=[system_message_created_by_user_id])
    recipients = relationship("SystemMessageRecipient", back_populates="message", cascade="all, delete-orphan")


class SystemMessageRecipient(Base):
    """Один получатель сообщения + отметка о прочтении (acked_at = NULL, пока не
    подтвердил). Один и тот же пользователь не может встретиться дважды у одного
    сообщения (uq-констрейнт) — на случай, если выбрали его и лично, и как «всех»."""

    __tablename__ = "system_message_recipients"
    __table_args__ = (
        UniqueConstraint("system_message_recipient_message_id", "system_message_recipient_user_id", name="uq_system_message_recipient"),
    )

    system_message_recipient_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    system_message_recipient_message_id: Mapped[int] = mapped_column(
        SQL_ID_TYPE, ForeignKey("system_messages.system_message_id", ondelete="CASCADE"), nullable=False, index=True
    )
    system_message_recipient_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    system_message_recipient_acked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    message = relationship("SystemMessage", back_populates="recipients")
    user = relationship("User")
