from datetime import datetime, timedelta

from app.models.messages import Message
from app.repositories.messages import MessageRepository
from app.services.messages import message_history, sync_messages

# Лента синка теперь фильтрует карточки по правам склада; для этих тестов (обычные
# текстовые сообщения) берём админа — обходит фильтрацию, ожидания прежние.
_ADMIN = {"user_admin": True, "user_id": 0}


def _make_message(db, user, *, text="hi", order_id=None):
    return MessageRepository(db).create(
        {
            "message_type": "message",
            "message_text": text,
            "message_owner_user_id": user.user_id,
            "message_order_id": order_id,
        }
    )


def _set_updated_at(db, message_id, when):
    db.query(Message).filter(Message.message_id == message_id).update(
        {Message.message_updated_at: when}
    )
    db.commit()


def test_sync_returns_changes_and_advances_cursor(db_session, existing_user):
    base = datetime(2026, 1, 1, 12, 0, 0)
    first = _make_message(db_session, existing_user, text="first")
    second = _make_message(db_session, existing_user, text="second")
    _set_updated_at(db_session, first.message_id, base)
    _set_updated_at(db_session, second.message_id, base + timedelta(seconds=1))

    initial = sync_messages(db_session, _ADMIN, cursor=None, limit=10)
    assert [item["message_id"] for item in initial["items"]] == [first.message_id, second.message_id]
    assert initial["has_more"] is False

    # Nothing changed since the returned cursor.
    follow_up = sync_messages(db_session, _ADMIN, cursor=initial["cursor"], limit=10)
    assert follow_up["items"] == []


def test_sync_paginates_with_has_more(db_session, existing_user):
    base = datetime(2026, 1, 1, 12, 0, 0)
    messages = [_make_message(db_session, existing_user, text=f"m{i}") for i in range(3)]
    for offset, message in enumerate(messages):
        _set_updated_at(db_session, message.message_id, base + timedelta(seconds=offset))

    page_one = sync_messages(db_session, _ADMIN, cursor=None, limit=2)
    assert [item["message_id"] for item in page_one["items"]] == [messages[0].message_id, messages[1].message_id]
    assert page_one["has_more"] is True

    page_two = sync_messages(db_session, _ADMIN, cursor=page_one["cursor"], limit=2)
    assert [item["message_id"] for item in page_two["items"]] == [messages[2].message_id]
    assert page_two["has_more"] is False


def test_sync_emits_tombstone_after_delete(db_session, existing_user):
    base = datetime(2026, 1, 1, 12, 0, 0)
    message = _make_message(db_session, existing_user, text="doomed")
    _set_updated_at(db_session, message.message_id, base)

    cursor = sync_messages(db_session, _ADMIN, cursor=None, limit=10)["cursor"]

    repository = MessageRepository(db_session)
    repository.delete(repository.get_by_id(message.message_id))
    _set_updated_at(db_session, message.message_id, base + timedelta(seconds=1))

    delta = sync_messages(db_session, _ADMIN, cursor=cursor, limit=10)
    assert len(delta["items"]) == 1
    assert delta["items"][0]["message_id"] == message.message_id
    assert delta["items"][0]["message_deleted"] is True


def test_initial_sync_skips_already_deleted(db_session, existing_user):
    base = datetime(2026, 1, 1, 12, 0, 0)
    message = _make_message(db_session, existing_user, text="gone")
    repository = MessageRepository(db_session)
    repository.delete(repository.get_by_id(message.message_id))
    _set_updated_at(db_session, message.message_id, base)

    # A fresh client (no cursor) should not learn about messages it never had.
    assert sync_messages(db_session, _ADMIN, cursor=None, limit=10)["items"] == []


def test_touch_for_order_marks_referencing_card(db_session, existing_user):
    base = datetime(2026, 1, 1, 12, 0, 0)
    card = _make_message(db_session, existing_user, text="order card", order_id=555)
    unrelated = _make_message(db_session, existing_user, text="plain")
    _set_updated_at(db_session, card.message_id, base)
    _set_updated_at(db_session, unrelated.message_id, base)

    cursor = sync_messages(db_session, _ADMIN, cursor=None, limit=10)["cursor"]

    touched = MessageRepository(db_session).touch_for_order(555)
    assert touched == [card.message_id]
    # Simulate the rotation onto a later tick so the delta is observable despite second precision.
    _set_updated_at(db_session, card.message_id, base + timedelta(seconds=1))

    delta = sync_messages(db_session, _ADMIN, cursor=cursor, limit=10)
    assert [item["message_id"] for item in delta["items"]] == [card.message_id]
    assert delta["items"][0]["message_deleted"] is False



def _set_created_at(db, message_id, when):
    db.query(Message).filter(Message.message_id == message_id).update(
        {Message.message_created_at: when, Message.message_updated_at: when}
    )
    db.commit()


def test_history_pages_newest_first_and_hands_over_to_sync(db_session, existing_user):
    # Первый вход: последние сообщения сразу, дальше страницы всё старше, без дублей и
    # пропусков; sync_cursor с первой страницы — точка продолжения дельта-синка.
    base = datetime(2026, 1, 1, 12, 0, 0)
    messages = [_make_message(db_session, existing_user, text=f"m{i}") for i in range(5)]
    for offset, message in enumerate(messages):
        _set_created_at(db_session, message.message_id, base + timedelta(seconds=offset))
    ids = [m.message_id for m in messages]

    first = message_history(db_session, _ADMIN, before=None, limit=2)
    assert [item["message_id"] for item in first["items"]] == [ids[4], ids[3]]
    assert first["has_more"] is True
    assert first["sync_cursor"]

    second = message_history(db_session, _ADMIN, before=first["before"], limit=2)
    assert [item["message_id"] for item in second["items"]] == [ids[2], ids[1]]
    assert "sync_cursor" not in second
    third = message_history(db_session, _ADMIN, before=second["before"], limit=2)
    assert [item["message_id"] for item in third["items"]] == [ids[0]]
    assert third["has_more"] is False

    # Пока грузилась история: одно сообщение изменили, одно удалили, одно добавили —
    # дельта-синк с sync_cursor отдаёт ровно это.
    repository = MessageRepository(db_session)
    _set_updated_at(db_session, ids[1], base + timedelta(minutes=1))
    repository.delete(repository.get_by_id(ids[2]))
    _set_updated_at(db_session, ids[2], base + timedelta(minutes=2))
    fresh = _make_message(db_session, existing_user, text="fresh")
    _set_updated_at(db_session, fresh.message_id, base + timedelta(minutes=3))

    delta = sync_messages(db_session, _ADMIN, cursor=first["sync_cursor"], limit=10)
    assert [item["message_id"] for item in delta["items"]] == [ids[1], ids[2], fresh.message_id]
    assert delta["items"][1]["message_deleted"] is True


def test_history_skips_deleted_messages(db_session, existing_user):
    base = datetime(2026, 1, 1, 12, 0, 0)
    kept = _make_message(db_session, existing_user, text="kept")
    gone = _make_message(db_session, existing_user, text="gone")
    _set_created_at(db_session, kept.message_id, base)
    _set_created_at(db_session, gone.message_id, base + timedelta(seconds=1))
    repository = MessageRepository(db_session)
    repository.delete(repository.get_by_id(gone.message_id))

    page = message_history(db_session, _ADMIN, before=None, limit=10)
    assert [item["message_id"] for item in page["items"]] == [kept.message_id]
