"""Системные сообщения из «Админки»: блокирующий оверлей в приложении, пока
получатель явно не подтвердит прочтение. Получатели фиксируются на момент
отправки (снимок), доставка — SSE-сигнал «перечитай список» (без содержимого
в эвенте — контент отдаём адресно, по текущему пользователю) + список
неподтверждённых сообщений при каждом старте приложения (на случай, если
получатель был оффлайн в момент отправки)."""
from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.system_messages import SystemMessage, SystemMessageRecipient
from app.repositories.users import UserRepository
from app.schemas.system_messages import SystemMessageCreatePayload
from app.services.serializers import serialize_datetime


def _resolve_target_users(db: Session, payload: SystemMessageCreatePayload) -> list:
    repo = UserRepository(db)

    if payload.target == "all":
        return repo.list_active()

    if payload.target == "user":
        if len(payload.user_ids) != 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для получателя «один» нужен ровно один user_id")
    elif not payload.user_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Выберите хотя бы одного получателя")

    users = repo.list_active_by_ids(payload.user_ids)
    if not users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Получатели не найдены")
    return users


def _user_name(user) -> str | None:
    if user is None:
        return None
    return f"{user.user_second_name} {user.user_first_name}".strip() or user.user_login


def _serialize_message_for_admin(message: SystemMessage) -> dict:
    recipients = message.recipients
    read_count = sum(1 for r in recipients if r.system_message_recipient_acked_at is not None)
    return {
        "id": message.system_message_id,
        "text": message.system_message_text,
        "important": message.system_message_important,
        "created_at": serialize_datetime(message.system_message_created_at),
        "created_by": {
            "user_id": message.system_message_created_by_user_id,
            "name": _user_name(message.created_by),
        },
        "recipients_count": len(recipients),
        "read_count": read_count,
    }


def create_system_message(db: Session, payload: SystemMessageCreatePayload, current_user: dict) -> dict:
    users = _resolve_target_users(db, payload)

    message = SystemMessage(
        system_message_text=payload.text.strip(),
        system_message_important=payload.important,
        system_message_created_by_user_id=current_user["user_id"],
    )
    db.add(message)
    db.flush()

    for user in users:
        db.add(
            SystemMessageRecipient(
                system_message_recipient_message_id=message.system_message_id,
                system_message_recipient_user_id=user.user_id,
            )
        )

    db.commit()
    db.refresh(message)

    # У получателей может быть открыто приложение прямо сейчас — просим их
    # перечитать список ожидающих сообщений. Содержимое в эвент не кладём —
    # список отдаёт GET /system-messages/pending, адресно по текущему юзеру.
    from app.services.message_stream import broker

    broker.publish({"type": "system_message_created"})

    return _serialize_message_for_admin(message)


def list_system_messages(db: Session) -> dict:
    messages = db.query(SystemMessage).order_by(SystemMessage.system_message_created_at.desc()).all()
    return {"items": [_serialize_message_for_admin(m) for m in messages]}


def get_system_message_receipts(db: Session, message_id: int) -> dict:
    message = db.get(SystemMessage, message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сообщение не найдено")

    items = [
        {
            "user_id": r.system_message_recipient_user_id,
            "name": _user_name(r.user),
            "acked_at": serialize_datetime(r.system_message_recipient_acked_at),
        }
        for r in message.recipients
    ]
    # Не подтвердившие — сверху (это и есть рабочий список «кого поторопить»).
    items.sort(key=lambda item: (item["acked_at"] is not None, item["name"] or ""))
    return {"items": items}


def list_pending_system_messages(db: Session, user_id: int) -> dict:
    rows = (
        db.query(SystemMessageRecipient)
        .join(SystemMessage, SystemMessage.system_message_id == SystemMessageRecipient.system_message_recipient_message_id)
        .filter(
            SystemMessageRecipient.system_message_recipient_user_id == user_id,
            SystemMessageRecipient.system_message_recipient_acked_at.is_(None),
        )
        .order_by(SystemMessage.system_message_created_at.asc())
        .all()
    )
    return {
        "items": [
            {
                "id": r.message.system_message_id,
                "text": r.message.system_message_text,
                "important": r.message.system_message_important,
                "created_at": serialize_datetime(r.message.system_message_created_at),
            }
            for r in rows
        ]
    }


def acknowledge_system_message(db: Session, message_id: int, user_id: int) -> dict:
    recipient = (
        db.query(SystemMessageRecipient)
        .filter(
            SystemMessageRecipient.system_message_recipient_message_id == message_id,
            SystemMessageRecipient.system_message_recipient_user_id == user_id,
        )
        .first()
    )
    if recipient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сообщение не адресовано вам")

    if recipient.system_message_recipient_acked_at is None:
        recipient.system_message_recipient_acked_at = datetime.utcnow()
        db.commit()

    return {"acked": True}
