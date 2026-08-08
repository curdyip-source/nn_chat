from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

SQL_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class TodoList(Base):
    """Пользовательский список задач («Личное», «Работа»). Умные списки (Входящие,
    Сегодня, Запланировано, Когда-нибудь, Архив) в базе не хранятся — они выводятся
    из полей самой задачи."""

    __tablename__ = "todo_lists"

    todo_list_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    todo_list_owner_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    todo_list_name: Mapped[str] = mapped_column(String(100), nullable=False)
    todo_list_position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    todo_list_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    owner = relationship("User")
    todos = relationship("Todo", back_populates="list")


class Todo(Base):
    __tablename__ = "todos"

    todo_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    todo_owner_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    # NULL = задача не в пользовательском списке (кандидат во «Входящие»).
    todo_list_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("todo_lists.todo_list_id", ondelete="SET NULL"), nullable=True, index=True)
    # Привязка к заказу: такая задача общая — её видит любой, кому виден сам заказ.
    # При удалении заказа задача остаётся, но теряет привязку (SET NULL), чтобы не
    # уносить с собой работу.
    todo_order_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("orders.order_id", ondelete="SET NULL"), nullable=True, index=True)
    todo_title: Mapped[str] = mapped_column(String(500), nullable=False)
    todo_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # «Когда сделать» и дедлайн — разные моменты (дата со временем): первый
    # раскладывает задачу по Сегодня/Запланировано, второй рисует флажок (красный,
    # если срок уже прошёл). Храним в UTC, без таймзоны — как остальные времена.
    todo_do_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    todo_deadline_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # «Когда-нибудь»: задача без даты, отложенная осознанно.
    todo_someday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    todo_tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    todo_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Архив — отдельный флаг: выполненная задача пару секунд ещё видна зачёркнутой
    # в своём списке и только потом уезжает в архив.
    todo_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0", index=True)
    todo_position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    todo_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    owner = relationship("User", foreign_keys=[todo_owner_user_id])
    list = relationship("TodoList", back_populates="todos")
    order = relationship("Order", back_populates="todos")
    subtasks = relationship("TodoSubtask", back_populates="todo", cascade="all, delete-orphan", order_by="TodoSubtask.todo_subtask_position")
    assignees = relationship("TodoAssignee", back_populates="todo", cascade="all, delete-orphan")


class TodoSubtask(Base):
    __tablename__ = "todo_subtasks"

    todo_subtask_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    todo_subtask_todo_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("todos.todo_id", ondelete="CASCADE"), nullable=False, index=True)
    todo_subtask_title: Mapped[str] = mapped_column(String(500), nullable=False)
    todo_subtask_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    todo_subtask_position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    todo = relationship("Todo", back_populates="subtasks")


class TodoAssignee(Base):
    """Ответственный за задачу. Их может быть несколько; назначение показывает задачу
    в тудулисте человека и шлёт ему пуш."""

    __tablename__ = "todo_assignees"
    __table_args__ = (UniqueConstraint("todo_assignee_todo_id", "todo_assignee_user_id", name="uq_todo_assignee"),)

    todo_assignee_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    todo_assignee_todo_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("todos.todo_id", ondelete="CASCADE"), nullable=False, index=True)
    todo_assignee_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    todo_assignee_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    todo = relationship("Todo", back_populates="assignees")
    user = relationship("User")
