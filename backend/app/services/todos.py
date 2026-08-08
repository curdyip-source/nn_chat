from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.orders import Order
from app.repositories.todos import TodoRepository
from app.repositories.users import UserRepository
from app.services.access_control import allowed_order_status_ids, list_visibility
from app.services.card_sync import notify_order_changed
from app.schemas.todos import (
    TodoCreatePayload,
    TodoListCreatePayload,
    TodoListUpdatePayload,
    TodoReorderPayload,
    TodoUpdatePayload,
)
from app.services.push_notifications import send_todo_assigned_push_event
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
        Запланировано, Когда-нибудь, Архив) считает клиент по полям задачи.

        Видно: свои задачи, задачи, где пользователь ответственный, и задачи
        заказов, которые он вправе видеть (те же склады и статусы, что в СРМ)."""
        user_id = current_user["user_id"]
        return {
            "lists": [serialize_todo_list(row) for row in self.repository.list_lists(user_id)],
            "items": [serialize_todo(row) for row in self.repository.list_visible(user_id, self._accessible_orders_filter(current_user))],
        }

    def _accessible_orders_filter(self, current_user: dict):
        """Условие по таблице orders «этот заказ виден пользователю»: склад в области
        видимости (или свой заказ на складе с view=own) и статус в разрешённых.
        None = без ограничений (администратор)."""
        full_ids, own_ids, user_id = list_visibility(self.db, current_user)
        statuses = allowed_order_status_ids(current_user)

        clauses = []
        if full_ids is not None:
            scope = []
            if full_ids:
                scope.append(Order.order_establishment_id.in_(full_ids))
            if own_ids:
                scope.append(and_(Order.order_establishment_id.in_(own_ids), Order.order_owner_user_id == user_id))
            if not scope:
                # Складов нет вовсе — заказных задач пользователь не видит.
                return Order.order_id.is_(None)
            clauses.append(or_(*scope))
        if statuses is not None:
            clauses.append(Order.order_status_id.in_(statuses))

        if not clauses:
            return None
        return and_(*clauses)

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
        if payload.todo_order_id is not None:
            self._ensure_order_accessible(payload.todo_order_id, current_user)
        assignees = self._validated_assignees(payload.assignee_user_ids)
        row = self.repository.add_todo(
            {
                "todo_owner_user_id": user_id,
                "todo_list_id": payload.todo_list_id,
                "todo_order_id": payload.todo_order_id,
                "todo_title": payload.todo_title.strip(),
                "todo_note": (payload.todo_note or "").strip() or None,
                "todo_do_at": _as_naive_utc(payload.todo_do_at),
                "todo_deadline_at": _as_naive_utc(payload.todo_deadline_at),
                "todo_someday": payload.todo_someday,
                "todo_tags": _normalized_tags(payload.todo_tags),
                "todo_position": self.repository.next_todo_position(user_id),
            },
            [item.model_dump() for item in payload.subtasks],
            assignees,
        )
        self._notify_assigned(row, assignees, current_user)
        self._notify_order_card(row.todo_order_id)
        return serialize_todo(row)

    def update_todo(self, todo_id: int, payload: TodoUpdatePayload, current_user: dict) -> dict:
        row = self._get_todo_or_404(todo_id, current_user)
        fields = payload.model_fields_set
        data: dict = {}
        previous_assignees = self.repository.current_assignee_ids(row)

        if "todo_title" in fields and payload.todo_title is not None:
            data["todo_title"] = payload.todo_title.strip()
        if "todo_list_id" in fields:
            if payload.todo_list_id is not None:
                self._get_list_or_404(payload.todo_list_id, current_user)
            data["todo_list_id"] = payload.todo_list_id
        if "todo_order_id" in fields:
            if payload.todo_order_id is not None:
                self._ensure_order_accessible(payload.todo_order_id, current_user)
            data["todo_order_id"] = payload.todo_order_id
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

        assignees = None
        if payload.assignee_user_ids is not None:
            assignees = self._validated_assignees(payload.assignee_user_ids)

        previous_order_id = row.todo_order_id
        updated = self.repository.update_todo(row, data, subtasks, assignees)
        # Бабл с числом задач живёт в карточке заказа — обновляем обе стороны, если
        # задачу перевесили с одного заказа на другой.
        self._notify_order_card(previous_order_id)
        if updated.todo_order_id != previous_order_id:
            self._notify_order_card(updated.todo_order_id)
        if assignees is not None:
            # Пуш только тем, кого назначили именно сейчас.
            self._notify_assigned(updated, [uid for uid in assignees if uid not in previous_assignees], current_user)
        return serialize_todo(updated)

    def delete_todo(self, todo_id: int, current_user: dict) -> None:
        row = self._get_todo_or_404(todo_id, current_user)
        # Вести задачу (править, закрывать) может любой, кому она видна, а удалять —
        # только автор или админ: как с сообщениями чата.
        if row.todo_owner_user_id != current_user["user_id"] and not current_user.get("user_admin"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Удалить задачу может только автор")
        order_id = row.todo_order_id
        self.repository.delete_todo(row)
        self._notify_order_card(order_id)

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
        """Задача доступна автору, ответственным и всем, кому виден её заказ.
        Права на заказную задачу такие же, как на сам заказ: видишь заказ — можешь
        и вести его задачи."""
        row = self.repository.get_todo_by_id(todo_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")

        user_id = current_user["user_id"]
        if row.todo_owner_user_id == user_id:
            return row
        if user_id in self.repository.current_assignee_ids(row):
            return row
        if row.todo_order_id is not None and self._is_order_accessible(row.todo_order_id, current_user):
            return row
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")

    def _notify_order_card(self, order_id: int | None) -> None:
        if order_id is not None:
            notify_order_changed(self.db, order_id)

    def _is_order_accessible(self, order_id: int, current_user: dict) -> bool:
        query = self.db.query(Order.order_id).filter(Order.order_id == order_id)
        condition = self._accessible_orders_filter(current_user)
        if condition is not None:
            query = query.filter(condition)
        return query.first() is not None

    def _ensure_order_accessible(self, order_id: int, current_user: dict) -> None:
        if not self._is_order_accessible(order_id, current_user):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")

    def _validated_assignees(self, user_ids: list[int]) -> list[int]:
        """Ответственным можно назначить любого активного пользователя — включая
        системных (cdek_helper, nufnaf.ru): они такие же участники чата."""
        unique = list(dict.fromkeys(user_ids))
        if not unique:
            return []
        known = {user.user_id for user in UserRepository(self.db).list_active_by_ids(unique)}
        unknown = [uid for uid in unique if uid not in known]
        if unknown:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ответственный не найден или отключён")
        return unique

    def _notify_assigned(self, row, user_ids: list[int], current_user: dict) -> None:
        recipients = [uid for uid in user_ids if uid != current_user["user_id"]]
        if not recipients:
            return
        sender_name = f"{current_user.get('user_second_name') or ''} {current_user.get('user_first_name') or ''}".strip() or current_user["user_login"]
        send_todo_assigned_push_event(
            self.db,
            recipient_user_ids=recipients,
            sender_name=sender_name,
            todo_title=row.todo_title,
            todo_id=row.todo_id,
            order_id=row.todo_order_id,
        )


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
