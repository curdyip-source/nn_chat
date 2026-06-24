import logging
import time

import httpx
import jwt
from sqlalchemy.orm import Session

from app.core.config import APNS_AUTH_KEY_P8, APNS_ENABLED, APNS_KEY_ID, APNS_TEAM_ID, APNS_TOPIC, APNS_USE_SANDBOX
from app.repositories.user_devices import UserDeviceRepository


logger = logging.getLogger("app.push")


def send_push_notification_event(
    db: Session,
    *,
    excluded_user_id: int,
    message_type: str,
    sender_name: str,
    message_text: str | None,
    entity_id: int,
) -> int:
    if not APNS_ENABLED:
        logger.info(
            "push.skipped_disabled",
            extra={
                "event_type": "push.skipped_disabled",
                "message_type": message_type,
                "entity_id": entity_id,
            },
        )
        return 0

    targets = UserDeviceRepository(db).list_active_for_other_users(excluded_user_id=excluded_user_id)
    if not targets:
        logger.info(
            "push.skipped_no_targets",
            extra={
                "event_type": "push.skipped_no_targets",
                "message_type": message_type,
                "entity_id": entity_id,
                "excluded_user_id": excluded_user_id,
            },
        )
        return 0

    title, body = build_notification_content(message_type=message_type, sender_name=sender_name, message_text=message_text, entity_id=entity_id)
    return _dispatch_to_devices(db, devices=targets, title=title, body=body, event_type=message_type, entity_id=entity_id)


def send_mention_push_event(
    db: Session,
    *,
    recipient_user_ids: list[int],
    sender_name: str,
    context: str,
    entity_id: int,
) -> int:
    if not APNS_ENABLED:
        logger.info(
            "push.mention.skipped_disabled",
            extra={"event_type": "push.mention.skipped_disabled", "context": context, "entity_id": entity_id},
        )
        return 0

    targets = UserDeviceRepository(db).list_active_for_users(user_ids=recipient_user_ids)
    if not targets:
        logger.info(
            "push.mention.skipped_no_targets",
            extra={"event_type": "push.mention.skipped_no_targets", "context": context, "entity_id": entity_id},
        )
        return 0

    normalized_sender_name = sender_name.strip() or "Пользователь"
    title = "Упоминание"
    body = f"{normalized_sender_name} вас отметил в чате"
    event_type = "mention_chat" if context == "chat" else "mention_order"
    return _dispatch_to_devices(db, devices=targets, title=title, body=body, event_type=event_type, entity_id=entity_id)


def send_order_change_push_event(
    db: Session,
    *,
    excluded_user_id: int,
    sender_name: str,
    order_id: int,
    added_count: int,
    removed_count: int,
) -> int:
    if not APNS_ENABLED:
        logger.info(
            "push.order_change.skipped_disabled",
            extra={"event_type": "push.order_change.skipped_disabled", "order_id": order_id},
        )
        return 0

    targets = UserDeviceRepository(db).list_active_for_other_users(excluded_user_id=excluded_user_id)
    if not targets:
        logger.info(
            "push.order_change.skipped_no_targets",
            extra={"event_type": "push.order_change.skipped_no_targets", "order_id": order_id},
        )
        return 0

    normalized_sender_name = sender_name.strip() or "Пользователь"
    title = "Заказ изменён"
    parts: list[str] = []
    if added_count > 0:
        parts.append("добавлен товар" if added_count == 1 else f"добавлено товаров: {added_count}")
    if removed_count > 0:
        parts.append("удалён товар" if removed_count == 1 else f"удалено товаров: {removed_count}")
    detail = ", ".join(parts) if parts else "изменён состав"
    body = f"{normalized_sender_name} изменил заказ №{order_id}: {detail}"
    return _dispatch_to_devices(db, devices=targets, title=title, body=body, event_type="order_updated", entity_id=order_id)


def _dispatch_to_devices(db: Session, *, devices, title: str, body: str, event_type: str, entity_id: int) -> int:
    token = build_apns_provider_token()
    sent_count = 0

    with httpx.Client(http2=True, timeout=10.0) as client:
        for device in devices:
            endpoint_base = _apns_endpoint_for_device(device)
            response = client.post(
                f"{endpoint_base}/3/device/{device.user_device_token}",
                headers={
                    "authorization": f"bearer {token}",
                    "apns-topic": APNS_TOPIC,
                    "apns-push-type": "alert",
                    "apns-priority": "10",
                },
                json={
                    "aps": {
                        "alert": {
                            "title": title,
                            "body": body,
                        },
                        "sound": "default",
                    },
                    "event_type": event_type,
                    "entity_id": entity_id,
                },
            )

            if response.status_code == 200:
                sent_count += 1
                continue

            logger.warning(
                "push.delivery_failed",
                extra={
                    "event_type": "push.delivery_failed",
                    "device_token": device.user_device_token,
                    "status_code": response.status_code,
                    "response_text": response.text,
                },
            )

            if response.status_code in {400, 410}:
                UserDeviceRepository(db).deactivate_token(device.user_device_token)

    logger.info(
        "push.sent_summary",
        extra={
            "event_type": "push.sent_summary",
            "notification_event_type": event_type,
            "entity_id": entity_id,
            "target_count": len(devices),
            "sent_count": sent_count,
        },
    )

    return sent_count


def _apns_endpoint_for_device(device) -> str:
    sandbox_base = "https://api.sandbox.push.apple.com"
    production_base = "https://api.push.apple.com"

    environment = getattr(device, "user_device_environment", None)
    if environment == "sandbox":
        return sandbox_base
    if environment == "production":
        return production_base

    # No per-device environment recorded (legacy rows): fall back to the global flag.
    return sandbox_base if APNS_USE_SANDBOX else production_base


def build_apns_provider_token() -> str:
    issued_at = int(time.time())
    with open(APNS_AUTH_KEY_P8, "r", encoding="utf-8") as key_file:
        private_key = key_file.read()
    return jwt.encode(
        {"iss": APNS_TEAM_ID, "iat": issued_at},
        private_key,
        algorithm="ES256",
        headers={"alg": "ES256", "kid": APNS_KEY_ID},
    )


def build_notification_content(*, message_type: str, sender_name: str, message_text: str | None, entity_id: int | None = None) -> tuple[str, str]:
    normalized_sender_name = sender_name.strip() or "Пользователь"
    normalized_text = (message_text or "").strip()
    number = f" №{entity_id}" if entity_id else ""

    if message_type == "order":
        return f"Новый заказ{number}", f"{normalized_sender_name} создал заказ{number}"
    if message_type == "inventory":
        return f"Новая инвентаризация{number}", f"{normalized_sender_name} создал инвентаризацию{number}"
    if message_type == "product_registration":
        return f"Новая приемка{number}", f"{normalized_sender_name} создал приемку{number}"
    if normalized_text:
        return "Новое сообщение", f"{normalized_sender_name}: {normalized_text}"
    return "Новое сообщение", f"Новое сообщение от {normalized_sender_name}"