"""Постинг накладных СДЭК в тред заказа от имени системного пользователя cdek_helper.

После создания заказа CDEK (асинхронно у CDEK) в фоне: ждём трек, генерим 2 печатные
формы (накладная + ШК), скачиваем PDF и постим их сообщением во внутренний чат заказа
(order_comments) — «Трек номер создан: …» + 2 PDF-вложения.
"""
from __future__ import annotations

import logging
import threading
import time
from uuid import uuid4

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.orders import Order
from app.models.users import User
from app.repositories.message_attachment_assets import MessageAttachmentAssetRepository
from app.schemas.messages import MessageAttachmentCreatePayload
from app.schemas.orders import OrderCommentCreatePayload
from app.services import cdek

logger = logging.getLogger("app.cdek")

CDEK_HELPER_LOGIN = "cdek_helper"


def ensure_cdek_helper(db) -> dict:
    """Get-or-create системный пользователь cdek_helper (неактивный, без входа)."""
    user = db.query(User).filter(User.user_login == CDEK_HELPER_LOGIN).first()
    if user is None:
        user = User(
            user_login=CDEK_HELPER_LOGIN,
            user_password=hash_password(uuid4().hex),  # непригодный для входа
            user_admin=False,
            user_active=False,
            user_first_name="СДЭК",
            user_second_name="Бот",
            user_age=0,
            user_address="",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return {
        "user_id": user.user_id,
        "user_login": user.user_login,
        "user_first_name": user.user_first_name,
        "user_second_name": user.user_second_name,
    }


def _store_pdf(db, owner_id: int, order_id: int, pdf: bytes, filename: str) -> MessageAttachmentCreatePayload:
    key = f"cdek/{order_id}/{uuid4().hex}.pdf"
    MessageAttachmentAssetRepository(db).create({
        "attachment_asset_owner_user_id": owner_id,
        "attachment_asset_storage_key": key,
        "attachment_asset_original_filename": filename,
        "attachment_asset_mime_type": "application/pdf",
        "attachment_asset_kind": "file",
        "attachment_asset_size_bytes": len(pdf),
        "attachment_asset_bytes": pdf,
    })
    return MessageAttachmentCreatePayload(
        attachment_kind="file",
        attachment_original_filename=filename,
        attachment_mime_type="application/pdf",
        attachment_storage_key=key,
        attachment_size_bytes=len(pdf),
    )


def _run(order_id: int) -> None:
    from app.services.orders import OrderService  # локальный импорт: избегаем цикла

    db = SessionLocal()
    try:
        order = db.get(Order, order_id)
        if order is None or not order.order_cdek_uuid:
            return
        uuid = order.order_cdek_uuid

        # 1) дождаться трека (заказ обработан у CDEK)
        track = order.order_cdek_track_number
        for _ in range(12):
            if track:
                break
            try:
                info = cdek.order_info(uuid)
            except cdek.CdekError:
                info = {}
            track = info.get("cdek_number")
            if track:
                order.order_cdek_track_number = str(track)
                db.commit()
                # Дописываем номер в событие аудита о создании накладной (трек пришёл асинхронно).
                from app.services import cdek_orders
                cdek_orders.record_waybill_track_in_audit(db, order_id, track)
                break
            time.sleep(1.5)

        # 2) обе печатные формы -> PDF
        inv_pdf = cdek.get_print_pdf(cdek.create_invoice_print(uuid), kind="invoice")
        bc_pdf = cdek.get_print_pdf(cdek.create_barcode_print(uuid, fmt="A6"), kind="barcode")

        # 3) сохранить как вложения от cdek_helper и запостить сообщение в тред заказа
        helper = ensure_cdek_helper(db)
        att_invoice = _store_pdf(db, helper["user_id"], order_id, inv_pdf, f"Накладная-{order_id}.pdf")
        att_barcode = _store_pdf(db, helper["user_id"], order_id, bc_pdf, f"ШК-{order_id}.pdf")
        text = f"Трек номер создан: {track}" if track else "Накладные СДЭК готовы"
        payload = OrderCommentCreatePayload(
            order_comment_text=text,
            attachments=[att_invoice, att_barcode],
            mentioned_user_ids=[],
        )
        # enforce_access=False: бот СДЭК без ролей на складах, но постит в свой же заказ.
        OrderService(db).add_order_comment(order_id, payload, helper, enforce_access=False)
        logger.info("CDEK: накладные заказа %s отправлены в чат (трек %s)", order_id, track)
    except Exception as exc:  # фон — не роняем процесс
        logger.warning("CDEK: не удалось отправить накладные заказа %s: %s", order_id, exc)
    finally:
        db.close()


def post_waybills_async(order_id: int) -> None:
    """Запустить постинг накладных в фоне (печать CDEK асинхронна, не блокируем запрос)."""
    threading.Thread(target=_run, args=(order_id,), daemon=True).start()
