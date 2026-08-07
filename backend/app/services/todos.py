from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.todos import TodoRepository
from app.schemas.todos import (
    TodoCreatePayload,
    TodoListCreatePayload,
    TodoListUpdatePayload,
    TodoReorderPayload,
    TodoUpdatePayload,
)
from app.services.serializers import serialize_todo, serialize_todo_list

MAX_TODO_LISTS = 30


def _as_naive_utc(value: datetime | None) -> datetime | None:
    """Клиент присылает момент со смещением («…T09:00:00+03:00»), а колонка —
    timestamp без таймзоны: приводим к UTC и снимаем смещение, как везде в проекте."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _normalized_tags(tags: list[str]) -> list[str]:
    cleaned = [tag.strip() for tag in tags if tag and tag.strip()]
    return list(dict.fromkeys(cleaned))[:20]


class TodoService:
    """Задачи личные: всё — в пределах текущего пользователя, без ролей и складов."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TodoRepository(db)

    def get_board(self, current_user: dict) -> dict:
        """Весь тудулист одним запросом: умные списки (Входящие, Сегодня,
        Запланировано, Когда-нибудь, Архив) считает клиент по полям задачи."""
        user_id = current_user["user_id"]
        return {
            "lists": [serialize_todo_list(row) for row in self.repository.list_lists(user_id)],
            "items": [serialize_todo(row) for row in self.repository.list_todos(user_id)],
        }

    # --- пользовательские списки ---

    def create_list(self, payload: TodoListCreatePayload, current_user: dict) -> dict:
        user_id = current_user["user_id"]
        if len(self.repository.list_lists(user_id)) >= MAX_TODO_LISTS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Можно завести не больше {MAX_TODO_LISTS} списков")
        row = self.repository.add_list(
            {
                "todo_list_owner_user_id": user_id,
                "todo_list_name": payload.todo_list_name.strip(),
                "todo_list_position": self.repository.next_list_position(user_id),
            }
        )
        return serialize_todo_list(row)

    def update_list(self, list_id: int, payload: TodoListUpdatePayload, current_user: dict) -> dict:
        row = self._get_list_or_404(list_id, current_user)
        return serialize_todo_list(self.repository.update_list(row, {"todo_list_name": payload.todo_list_name.strip()}))

    def delete_list(self, list_id: int, current_user: dict) -> None:
        row = self._get_list_or_404(list_id, current_user)
        self.repository.delete_list(row)

    # --- задачи ---

    def create_todo(self, payload: TodoCreatePayload, current_user: dict) -> dict:
        user_id = current_user["user_id"]
        if payload.todo_list_id is not None:
            self._get_list_or_404(payload.todo_list_id, current_user)
        row = self.repository.add_todo(
            {
                "todo_owner_user_id": user_id,
                "todo_list_id": payload.todo_list_id,
                "todo_title": payload.todo_title.strip(),
                "todo_note": (payload.todo_note or "").strip() or None,
                "todo_do_at": _as_naive_utc(payload.todo_do_at),
                "todo_deadline_at": _as_naive_utc(payload.todo_deadline_at),
                "todo_someday": payload.todo_someday,
                "todo_tags": _normalized_tags(payload.todo_tags),
                "todo_position": self.repository.next_todo_position(user_id),
            },
            [item.model_dump() for item in payload.subtasks],
        )
        return serialize_todo(row)

    def update_todo(self, todo_id: int, payload: TodoUpdatePayload, current_user: dict) -> dict:
        row = self._get_todo_or_404(todo_id, current_user)
        fields = payload.model_fields_set
        data: dict = {}

        if "todo_title" in fields and payload.todo_title is not None:
            data["todo_title"] = payload.todo_title.strip()
        if "todo_list_id" in fields:
            if payload.todo_list_id is not None:
                self._get_list_or_404(payload.todo_list_id, current_user)
            data["todo_list_id"] = payload.todo_list_id
        if "todo_note" in fields:
            data["todo_note"] = (payload.todo_note or "").strip() or None
        if "todo_do_at" in fields:
            data["todo_do_at"] = _as_naive_utc(payload.todo_do_at)
        if "todo_deadline_at" in fields:
            data["todo_deadline_at"] = _as_naive_utc(payload.todo_deadline_at)
        if "todo_someday" in fields and payload.todo_someday is not None:
            data["todo_someday"] = payload.todo_someday
        if "todo_tags" in fields:
            data["todo_tags"] = _normalized_tags(payload.todo_tags or [])
        if "todo_completed" in fields and payload.todo_completed is not None:
            # Момент выполнения ставим на сервере: клиенту незачем присылать своё время.
            data["todo_completed_at"] = datetime.utcnow() if payload.todo_completed else None
            if not payload.todo_completed:
                # Сняли галочку — задача возвращается из архива в работу.
                data["todo_archived"] = False
        if "todo_archived" in fields and payload.todo_archived is not None:
            data["todo_archived"] = payload.todo_archived

        subtasks = None
        if payload.subtasks is not None:
            subtasks = [item.model_dump() for item in payload.subtasks]

        return serialize_todo(self.repository.update_todo(row, data, subtasks))

    def delete_todo(self, todo_id: int, current_user: dict) -> None:
        row = self._get_todo_or_404(todo_id, current_user)
        self.repository.delete_todo(row)

    def reorder_todos(self, payload: TodoReorderPayload, current_user: dict) -> dict:
        positions = {item.todo_id: item.todo_position for item in payload.items}
        self.repository.reorder_todos(current_user["user_id"], positions)
        return self.get_board(current_user)

    def _get_list_or_404(self, list_id: int, current_user: dict):
        row = self.repository.get_list(current_user["user_id"], list_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Список не найден")
        return row

    def _get_todo_or_404(self, todo_id: int, current_user: dict):
        row = self.repository.get_todo(current_user["user_id"], todo_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
        return row


def get_todo_board(db: Session, current_user: dict) -> dict:
    return TodoService(db).get_board(current_user)


def create_todo_list(db: Session, payload: TodoListCreatePayload, current_user: dict) -> dict:
    return TodoService(db).create_list(payload, current_user)


def update_todo_list(db: Session, list_id: int, payload: TodoListUpdatePayload, current_user: dict) -> dict:
    return TodoService(db).update_list(list_id, payload, current_user)


def delete_todo_list(db: Session, list_id: int, current_user: dict) -> None:
    TodoService(db).delete_list(list_id, current_user)


def create_todo(db: Session, payload: TodoCreatePayload, current_user: dict) -> dict:
    return TodoService(db).create_todo(payload, current_user)


def update_todo(db: Session, todo_id: int, payload: TodoUpdatePayload, current_user: dict) -> dict:
    return TodoService(db).update_todo(todo_id, payload, current_user)


def delete_todo(db: Session, todo_id: int, current_user: dict) -> None:
    TodoService(db).delete_todo(todo_id, current_user)


def reorder_todos(db: Session, payload: TodoReorderPayload, current_user: dict) -> dict:
    return TodoService(db).reorder_todos(payload, current_user)
