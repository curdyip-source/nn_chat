from urllib.parse import quote

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.message_attachments import get_message_attachment_content
from app.services.order_comment_attachments import get_order_comment_attachment_content
from app.services.profile_photos import get_profile_photo_content


router = APIRouter(prefix="/media", tags=["media"])


@router.get("/profile-photos/{user_id}")
def get_profile_photo_route(user_id: int, db: Session = Depends(get_db)) -> Response:
    photo = get_profile_photo_content(db, user_id)
    return Response(
        content=photo.content,
        media_type=photo.mime_type,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/message-attachments/{attachment_id}")
def get_message_attachment_route(attachment_id: int, db: Session = Depends(get_db)) -> Response:
    attachment = get_message_attachment_content(db, attachment_id)
    encoded_filename = quote(attachment.filename)
    return Response(
        content=attachment.content,
        media_type=attachment.mime_type,
        headers={
            "Cache-Control": "public, max-age=300",
            "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}",
        },
    )


@router.get("/order-comment-attachments/{attachment_id}")
def get_order_comment_attachment_route(attachment_id: int, db: Session = Depends(get_db)) -> Response:
    attachment = get_order_comment_attachment_content(db, attachment_id)
    encoded_filename = quote(attachment.filename)
    return Response(
        content=attachment.content,
        media_type=attachment.mime_type,
        headers={
            "Cache-Control": "public, max-age=300",
            "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}",
        },
    )