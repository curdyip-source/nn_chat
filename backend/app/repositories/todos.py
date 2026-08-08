from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.orders import Order
from app.models.todos import Todo, TodoAssignee, TodoList, TodoSubtask


class TodoRepository:
    """Всё строго в пределах одного пользователя: задачи личные, чужих не видно."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # --- списки ---

    def list_lists(self, user_id: int) -> list[TodoList]:
        return (
            self.db.query(TodoList)
            .filter(TodoList.todo_list_owner_user_id == user_id)
            .order_by(TodoList.todo_list_position, TodoList.todo_list_id)
            .all()
        )

    def get_list(self, user_id: int, list_id: int) -> TodoList | None:
        return (
            self.db.query(TodoList)
            .filter(TodoList.todo_list_id == list_id, TodoList.todo_list_owner_user_id == user_id)
            .first()
        )

    def next_list_position(self, user_id: int) -> int:
        value = (
            self.db.query(func.max(TodoList.todo_list_position))
            .filter(TodoList.todo_list_owner_user_id == user_id)
            .scalar()
        )
        return (value or 0) + 1

    def add_list(self, data: dict) -> TodoList:
        row = TodoList(**data)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update_list(self, row: TodoList, data: dict) -> TodoList:
        for key, value in data.items():
            setattr(row, key, value)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_list(self, row: TodoList) -> None:
        # Задачи не удаляем: FK ondelete=SET NULL вернёт их во «Входящие».
        self.db.query(Todo).filter(Todo.todo_list_id == row.todo_list_id).update({Todo.todo_list_id: None})
        self.db.delete(row)
        self.db.commit()

    # --- задачи ---

    def list_visible(self, user_id: int, accessible_orders_filter) -> list[Todo]:
        """Задачи, доступные пользователю: свои, где он ответственный, и задачи
        заказов, которые он вправе видеть. `accessible_orders_filter` — готовое
        условие по таблице orders (его собирает сервис из прав на склады и статусы)
        либо None, если пользователь видит все заказы (администратор)."""
        assigned = self.db.query(TodoAssignee.todo_assignee_todo_id).filter(TodoAssignee.todo_assignee_user_id == user_id)
        order_ids = self.db.query(Order.order_id)
        if accessible_orders_filter is not None:
            order_ids = order_ids.filter(accessible_orders_filter)

        return (
            self._todo_query()
            .filter(
                or_(
                    Todo.todo_owner_user_id == user_id,
                    Todo.todo_id.in_(assigned),
                    Todo.todo_order_id.in_(order_ids),
                )
            )
            .order_by(Todo.todo_position, Todo.todo_id)
            .all()
        )

    def get_todo_by_id(self, todo_id: int) -> Todo | None:
        return self._todo_query().filter(Todo.todo_id == todo_id).first()

    def get_todo(self, user_id: int, todo_id: int) -> Todo | None:
        return self._todo_query().filter(Todo.todo_id == todo_id, Todo.todo_owner_user_id == user_id).first()

    def list_todos_for_order(self, order_id: int) -> list[Todo]:
        return self._todo_query().filter(Todo.todo_order_id == order_id).order_by(Todo.todo_id).all()

    def _todo_query(self):
        return self.db.query(Todo).options(
            joinedload(Todo.subtasks),
            joinedload(Todo.assignees).joinedload(TodoAssignee.user),
            joinedload(Todo.owner),
        )

    def next_todo_position(self, user_id: int) -> int:
        value = self.db.query(func.max(Todo.todo_position)).filter(Todo.todo_owner_user_id == user_id).scalar()
        return (value or 0) + 1

    def add_todo(self, data: dict, subtasks: list[dict], assignee_user_ids: list[int]) -> Todo:
        row = Todo(**data)
        self.db.add(row)
        self.db.flush()
        self._replace_subtasks(row, subtasks)
        self._replace_assignees(row, assignee_user_ids)
        self.db.commit()
        return self.get_todo_by_id(row.todo_id)

    def update_todo(self, row: Todo, data: dict, subtasks: list[dict] | None = None, assignee_user_ids: list[int] | None = None) -> Todo:
        for key, value in data.items():
            setattr(row, key, value)
        if subtasks is not None:
            self._replace_subtasks(row, subtasks)
        if assignee_user_ids is not None:
            self._replace_assignees(row, assignee_user_ids)
        self.db.commit()
        return self.get_todo_by_id(row.todo_id)

    def delete_todo(self, row: Todo) -> None:
        self.db.delete(row)
        self.db.commit()

    def current_assignee_ids(self, row: Todo) -> set[int]:
        return {item.todo_assignee_user_id for item in row.assignees}

    def reorder_todos(self, user_id: int, positions: dict[int, int]) -> None:
        rows = self.db.query(Todo).filter(Todo.todo_owner_user_id == user_id, Todo.todo_id.in_(positions.keys())).all()
        for row in rows:
            row.todo_position = positions[row.todo_id]
        self.db.commit()

    def _replace_subtasks(self, row: Todo, subtasks: list[dict]) -> None:
        # Подзадачи редактируются целиком вместе с карточкой — переписываем список,
        # не пытаясь сопоставлять существующие по id. Работаем через коллекцию
        # (cascade="all, delete-orphan" удалит старые), чтобы сессия не разъезжалась
        # с базой, как было бы после bulk-delete запросом.
        row.subtasks.clear()
        self.db.flush()
        for index, item in enumerate(subtasks):
            row.subtasks.append(
                TodoSubtask(
                    todo_subtask_title=item["todo_subtask_title"],
                    todo_subtask_done=item.get("todo_subtask_done", False),
                    todo_subtask_position=index,
                )
            )
        self.db.flush()

    def _replace_assignees(self, row: Todo, user_ids: list[int]) -> None:
        row.assignees.clear()
        self.db.flush()
        for user_id in dict.fromkeys(user_ids):
            row.assignees.append(TodoAssignee(todo_assignee_user_id=user_id))
        self.db.flush()
