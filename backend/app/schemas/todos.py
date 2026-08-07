from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TodoListCreatePayload(BaseModel):
    todo_list_name: str = Field(min_length=1, max_length=100)


class TodoListUpdatePayload(BaseModel):
    todo_list_name: str = Field(min_length=1, max_length=100)


class TodoSubtaskPayload(BaseModel):
    todo_subtask_title: str = Field(min_length=1, max_length=500)
    todo_subtask_done: bool = False


class TodoCreatePayload(BaseModel):
    todo_title: str = Field(min_length=1, max_length=500)
    todo_list_id: Optional[int] = None
    todo_note: Optional[str] = Field(default=None, max_length=4000)
    todo_do_at: Optional[datetime] = None
    todo_deadline_at: Optional[datetime] = None
    todo_someday: bool = False
    todo_tags: list[str] = Field(default_factory=list, max_length=20)
    subtasks: list[TodoSubtaskPayload] = Field(default_factory=list, max_length=50)


class TodoUpdatePayload(BaseModel):
    """Частичное обновление: присланы только изменённые поля. Отличаем «поле не
    прислали» от «прислали null» через model_fields_set, поэтому дату можно и
    поставить, и снять."""

    todo_title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    todo_list_id: Optional[int] = None
    todo_note: Optional[str] = Field(default=None, max_length=4000)
    todo_do_at: Optional[datetime] = None
    todo_deadline_at: Optional[datetime] = None
    todo_someday: Optional[bool] = None
    todo_tags: Optional[list[str]] = Field(default=None, max_length=20)
    todo_completed: Optional[bool] = None
    todo_archived: Optional[bool] = None
    subtasks: Optional[list[TodoSubtaskPayload]] = Field(default=None, max_length=50)


class TodoReorderItem(BaseModel):
    todo_id: int
    todo_position: int = Field(ge=0)


class TodoReorderPayload(BaseModel):
    items: list[TodoReorderItem] = Field(min_length=1, max_length=500)
