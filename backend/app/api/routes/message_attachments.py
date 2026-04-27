from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.services.message_attachments import upload_message_attachment


router = APIRouter(prefix="/message-attachments", tags=["message-attachments"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_message_attachment_route(
    attachment_kind: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return {"item": await upload_message_attachment(db, current_user=current_user, file=file, attachment_kind=attachment_kind)}