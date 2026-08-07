from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.todos import (
    TodoCreatePayload,
    TodoListCreatePayload,
    TodoListUpdatePayload,
    TodoReorderPayload,
    TodoUpdatePayload,
)
from app.services.todos import (
    create_todo,
    create_todo_list,
    delete_todo,
    delete_todo_list,
    get_todo_board,
    reorder_todos,
    update_todo,
    update_todo_list,
)

router = APIRouter(prefix="/todos", tags=["todos"])
lists_router = APIRouter(prefix="/todo-lists", tags=["todos"])


@router.get("")
def get_todos(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Списки и все задачи пользователя разом: тудулист личный и небольшой, а
    раскладку по умным спискам делает клиент."""
    return get_todo_board(db, current_user)


@router.post("", status_code=status.HTTP_201_CREATED)
def add_todo(payload: TodoCreatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": create_todo(db, payload, current_user)}


@router.put("/reorder")
def reorder(payload: TodoReorderPayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return reorder_todos(db, payload, current_user)


@router.put("/{todo_id}")
def edit_todo(todo_id: int, payload: TodoUpdatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": update_todo(db, todo_id, payload, current_user)}


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_todo(todo_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    delete_todo(db, todo_id, current_user)


@lists_router.post("", status_code=status.HTTP_201_CREATED)
def add_todo_list(payload: TodoListCreatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": create_todo_list(db, payload, current_user)}


@lists_router.put("/{list_id}")
def rename_todo_list(list_id: int, payload: TodoListUpdatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": update_todo_list(db, list_id, payload, current_user)}


@lists_router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_todo_list(list_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    delete_todo_list(db, list_id, current_user)
