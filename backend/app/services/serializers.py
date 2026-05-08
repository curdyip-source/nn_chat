from datetime import datetime, timezone
from decimal import Decimal


def serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def serialize_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def serialize_user(row) -> dict:
    verified_by = getattr(row, "verified_by", None)
    return {
        "user_id": row.user_id,
        "user_login": row.user_login,
        "user_admin": row.user_admin,
        "user_active": row.user_active,
        "user_first_name": row.user_first_name,
        "user_second_name": row.user_second_name,
        "user_profile_photo": row.user_profile_photo,
        "user_age": row.user_age,
        "user_address": row.user_address,
        "user_verified_user_id": row.user_verified_user_id,
        "user_verified_user_login": verified_by.user_login if verified_by else None,
        "user_created_at": serialize_datetime(row.user_created_at),
    }


def serialize_user_session(row, *, is_current: bool = False) -> dict:
    return {
        "session_id": row.session_id,
        "session_created_at": serialize_datetime(row.session_created_at),
        "session_expires_at": serialize_datetime(row.session_expires_at),
        "is_current": is_current,
    }


def serialize_document(row) -> dict:
    owner = getattr(row, "owner", None)
    verified_by = getattr(row, "verified_by", None)
    return {
        "document_id": row.document_id,
        "document_owner_user_id": row.document_owner_user_id,
        "document_kind": row.document_kind,
        "document_original_filename": row.document_original_filename,
        "document_mime_type": row.document_mime_type,
        "document_storage_key": row.document_storage_key,
        "document_status": row.document_status,
        "document_note": row.document_note,
        "document_size_bytes": row.document_size_bytes,
        "document_created_at": serialize_datetime(row.document_created_at),
        "document_verified_at": serialize_datetime(row.document_verified_at),
        "owner_login": owner.user_login if owner else None,
        "verified_by_login": verified_by.user_login if verified_by else None,
    }


def serialize_audit_event(row) -> dict:
    actor = getattr(row, "actor", None)
    return {
        "audit_event_id": row.audit_event_id,
        "actor_user_id": row.actor_user_id,
        "actor_user_login": actor.user_login if actor else None,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "event_type": row.event_type,
        "event_payload": row.event_payload,
        "request_id": row.request_id,
        "ip_address": row.ip_address,
        "user_agent": row.user_agent,
        "created_at": serialize_datetime(row.created_at),
    }


def serialize_establishment(row) -> dict:
    owner = getattr(row, "owner", None)
    return {
        "establishment_id": row.establishment_id,
        "establishment_name": row.establishment_name,
        "establishment_address": row.establishment_address,
        "establishment_owner_user_id": row.establishment_owner_user_id,
        "establishment_owner_user_login": owner.user_login if owner else None,
        "establishment_created_at": serialize_datetime(row.establishment_created_at),
    }


def serialize_order_method(row) -> dict:
    owner = getattr(row, "owner", None)
    return {
        "order_method_id": row.order_method_id,
        "order_method_name": row.order_method_name,
        "order_method_sub_methods": row.order_method_sub_methods or [],
        "order_method_owner_user_id": row.order_method_owner_user_id,
        "order_method_owner_user_login": owner.user_login if owner else None,
        "order_method_created_at": serialize_datetime(row.order_method_created_at),
    }


def serialize_status(row) -> dict:
    owner = getattr(row, "owner", None)
    return {
        "status_id": row.status_id,
        "status_type": row.status_type,
        "status_status": row.status_status,
        "status_color": row.status_color,
        "status_owner_user_id": row.status_owner_user_id,
        "status_owner_user_login": owner.user_login if owner else None,
        "status_created_at": serialize_datetime(row.status_created_at),
    }


def serialize_currency(row) -> dict:
    owner = getattr(row, "owner", None)
    return {
        "currency_id": row.currency_id,
        "currency_name": row.currency_name,
        "currency_sign": row.currency_sign,
        "currency_owner_user_id": row.currency_owner_user_id,
        "currency_owner_user_login": owner.user_login if owner else None,
        "currency_created_at": serialize_datetime(row.currency_created_at),
    }


def serialize_product(row) -> dict:
    owner = getattr(row, "owner", None)
    return {
        "product_id": row.product_id,
        "product_article": row.product_article,
        "product_name": row.product_name,
        "product_cost_usd": serialize_decimal(row.product_cost_usd),
        "product_owner_user_id": row.product_owner_user_id,
        "product_owner_user_login": owner.user_login if owner else None,
        "product_created_at": serialize_datetime(row.product_created_at),
    }


def serialize_contact(row) -> dict:
    establishment = getattr(row, "establishment", None)
    order_method = getattr(row, "order_method", None)
    owner = getattr(row, "owner", None)
    return {
        "contact_id": row.contact_id,
        "contact_type": row.contact_type,
        "contact_name": row.contact_name,
        "contact_info": row.contact_info,
        "contact_establishment_id": row.contact_establishment_id,
        "contact_establishment_name": establishment.establishment_name if establishment else None,
        "contact_order_method_id": row.contact_order_method_id,
        "contact_order_method_name": order_method.order_method_name if order_method else None,
        "contact_order_sub_method": row.contact_order_sub_method,
        "contact_owner_user_id": row.contact_owner_user_id,
        "contact_owner_user_login": owner.user_login if owner else None,
        "contact_created_at": serialize_datetime(row.contact_created_at),
    }


def serialize_message_attachment(row) -> dict:
    return {
        "attachment_id": row.attachment_id,
        "attachment_kind": row.attachment_kind,
        "attachment_original_filename": row.attachment_original_filename,
        "attachment_mime_type": row.attachment_mime_type,
        "attachment_storage_key": row.attachment_storage_key,
        "attachment_size_bytes": row.attachment_size_bytes,
        "attachment_created_at": serialize_datetime(row.attachment_created_at),
    }


def serialize_order_item(row) -> dict:
    status = getattr(row, "status", None)
    source_establishment = getattr(row, "source_establishment", None)
    destination_establishment = getattr(row, "destination_establishment", None)
    return {
        "order_item_id": row.order_item_id,
        "order_item_product_id": row.order_item_product_id,
        "order_item_name": row.order_item_name,
        "order_item_article": row.order_item_article,
        "order_item_quantity": row.order_item_quantity,
        "order_item_price": serialize_decimal(row.order_item_price),
        "order_item_status_id": row.order_item_status_id,
        "order_item_status": status.status_status if status else None,
        "order_item_status_color": status.status_color if status else None,
        "order_item_source_establishment_id": row.order_item_source_establishment_id,
        "order_item_source_establishment_name": source_establishment.establishment_name if source_establishment else None,
        "order_item_destination_establishment_id": row.order_item_destination_establishment_id,
        "order_item_destination_establishment_name": destination_establishment.establishment_name if destination_establishment else None,
        "order_item_currency_id": row.order_item_currency_id,
        "order_item_checkpoint_started": row.order_item_checkpoint_started,
        "order_item_checkpoint_completed": row.order_item_checkpoint_completed,
        "order_item_created_at": serialize_datetime(row.order_item_created_at),
    }


def serialize_order_comment(row) -> dict:
    owner = getattr(row, "owner", None)
    return {
        "order_comment_id": row.order_comment_id,
        "order_comment_order_id": row.order_comment_order_id,
        "order_comment_text": row.order_comment_text,
        "order_comment_owner_user_id": row.order_comment_owner_user_id,
        "order_comment_owner_user_login": owner.user_login if owner else None,
        "order_comment_owner_first_name": owner.user_first_name if owner else None,
        "order_comment_owner_second_name": owner.user_second_name if owner else None,
        "order_comment_owner_profile_photo": owner.user_profile_photo if owner else None,
        "order_comment_created_at": serialize_datetime(row.order_comment_created_at),
        "attachments": [serialize_message_attachment(item) for item in getattr(row, "attachments", [])],
    }


def serialize_order(row) -> dict:
    establishment = getattr(row, "establishment", None)
    order_method = getattr(row, "order_method", None)
    status = getattr(row, "status", None)
    owner = getattr(row, "owner", None)
    comments = sorted(
        getattr(row, "comments", []),
        key=lambda item: (serialize_datetime(getattr(item, "order_comment_created_at", None)) or "", getattr(item, "order_comment_id", 0)),
    )
    return {
        "order_id": row.order_id,
        "order_establishment_id": row.order_establishment_id,
        "order_establishment_name": establishment.establishment_name if establishment else None,
        "order_method_id": row.order_method_id,
        "order_method_name": order_method.order_method_name if order_method else None,
        "order_sub_method": row.order_sub_method,
        "order_customer": row.order_customer,
        "order_info": row.order_info,
        "order_status_id": row.order_status_id,
        "order_status": status.status_status if status else None,
        "order_status_color": status.status_color if status else None,
        "order_owner_user_id": row.order_owner_user_id,
        "order_owner_user_login": owner.user_login if owner else None,
        "order_created_at": serialize_datetime(row.order_created_at),
        "items": [serialize_order_item(item) for item in getattr(row, "items", [])],
        "comments": [serialize_order_comment(item) for item in comments],
    }


def serialize_inventory_item(row) -> dict:
    return {
        "inventory_item_id": row.inventory_item_id,
        "inventory_item_product_id": row.inventory_item_product_id,
        "inventory_item_name": row.inventory_item_name,
        "inventory_item_article": row.inventory_item_article,
        "inventory_item_quantity": row.inventory_item_quantity,
        "inventory_item_cost": serialize_decimal(row.inventory_item_cost),
        "inventory_item_currency_id": row.inventory_item_currency_id,
        "inventory_item_created_at": serialize_datetime(row.inventory_item_created_at),
    }


def serialize_inventory(row) -> dict:
    establishment = getattr(row, "establishment", None)
    status = getattr(row, "status", None)
    owner = getattr(row, "owner", None)
    return {
        "inventory_id": row.inventory_id,
        "inventory_establishment_id": row.inventory_establishment_id,
        "inventory_establishment_name": establishment.establishment_name if establishment else None,
        "inventory_supplier": row.inventory_supplier,
        "inventory_status_id": row.inventory_status_id,
        "inventory_status": status.status_status if status else None,
        "inventory_status_color": status.status_color if status else None,
        "inventory_owner_user_id": row.inventory_owner_user_id,
        "inventory_owner_user_login": owner.user_login if owner else None,
        "inventory_created_at": serialize_datetime(row.inventory_created_at),
        "items": [serialize_inventory_item(item) for item in getattr(row, "items", [])],
    }


def serialize_product_registration_item(row) -> dict:
    return {
        "product_registration_item_id": row.product_registration_item_id,
        "product_registration_item_product_id": row.product_registration_item_product_id,
        "product_registration_item_name": row.product_registration_item_name,
        "product_registration_item_article": row.product_registration_item_article,
        "product_registration_item_quantity": row.product_registration_item_quantity,
        "product_registration_item_cost": serialize_decimal(row.product_registration_item_cost),
        "product_registration_item_currency_id": row.product_registration_item_currency_id,
        "product_registration_item_created_at": serialize_datetime(row.product_registration_item_created_at),
    }


def serialize_product_registration(row) -> dict:
    establishment = getattr(row, "establishment", None)
    status = getattr(row, "status", None)
    owner = getattr(row, "owner", None)
    return {
        "product_registration_id": row.product_registration_id,
        "product_registration_establishment_id": row.product_registration_establishment_id,
        "product_registration_establishment_name": establishment.establishment_name if establishment else None,
        "product_registration_supplier": row.product_registration_supplier,
        "product_registration_status_id": row.product_registration_status_id,
        "product_registration_status": status.status_status if status else None,
        "product_registration_status_color": status.status_color if status else None,
        "product_registration_owner_user_id": row.product_registration_owner_user_id,
        "product_registration_owner_user_login": owner.user_login if owner else None,
        "product_registration_created_at": serialize_datetime(row.product_registration_created_at),
        "items": [serialize_product_registration_item(item) for item in getattr(row, "items", [])],
    }


def serialize_message(row) -> dict:
    owner = getattr(row, "owner", None)
    order = getattr(row, "order", None)
    inventory = getattr(row, "inventory", None)
    product_registration = getattr(row, "product_registration", None)
    message_status = None
    message_status_color = None
    if order is not None and getattr(order, "status", None) is not None:
        message_status = order.status.status_status
        message_status_color = order.status.status_color
    elif inventory is not None and getattr(inventory, "status", None) is not None:
        message_status = inventory.status.status_status
        message_status_color = inventory.status.status_color
    elif product_registration is not None and getattr(product_registration, "status", None) is not None:
        message_status = product_registration.status.status_status
        message_status_color = product_registration.status.status_color
    return {
        "message_id": row.message_id,
        "message_type": row.message_type,
        "message_text": row.message_text,
        "message_owner_user_id": row.message_owner_user_id,
        "message_owner_user_login": owner.user_login if owner else None,
        "message_owner_first_name": owner.user_first_name if owner else None,
        "message_owner_second_name": owner.user_second_name if owner else None,
        "message_owner_profile_photo": owner.user_profile_photo if owner else None,
        "message_order_id": row.message_order_id,
        "message_inventory_id": row.message_inventory_id,
        "message_product_registration_id": row.message_product_registration_id,
        "message_status": message_status,
        "message_status_color": message_status_color,
        "message_created_at": serialize_datetime(row.message_created_at),
        "attachments": [serialize_message_attachment(item) for item in getattr(row, "attachments", [])],
        "order": serialize_order(order) if order else None,
        "inventory": serialize_inventory(inventory) if inventory else None,
        "product_registration": serialize_product_registration(product_registration) if product_registration else None,
    }