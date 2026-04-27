from pydantic import BaseModel
from math import ceil


def model_to_dict(model: BaseModel) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_unset=True)
    return model.dict(exclude_unset=True)


def build_pagination(page: int, page_size: int, total: int) -> dict:
    total_pages = ceil(total / page_size) if page_size else 0
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }