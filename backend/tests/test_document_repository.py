from app.repositories.documents import DocumentRepository


def test_document_repository_create_and_list_for_owner(db_session, existing_user):
    repository = DocumentRepository(db_session)

    created = repository.create(
        {
            "document_owner_user_id": existing_user.user_id,
            "document_kind": "passport",
            "document_original_filename": "passport.jpg",
            "document_mime_type": "image/jpeg",
            "document_storage_key": "docs/passport-1.jpg",
            "document_status": "pending",
            "document_note": "front side",
            "document_size_bytes": 1024,
        }
    )
    items, total = repository.list_for_user(user_id=existing_user.user_id, is_admin=False, kind="passport", status="pending", page=1, page_size=10)

    assert created.document_id is not None
    assert total == 1
    assert items[0].document_storage_key == "docs/passport-1.jpg"