from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.schemas.reference_data import ProductCreatePayload, ProductUpdatePayload
from app.services.reference_data import create_product, get_product_import_job, import_products_from_xlsx, list_products, update_product

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
def get_products(
    _: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="product_id"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> dict:
    return list_products(db, search=search, page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_product_route(payload: ProductCreatePayload, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"item": create_product(db, payload, current_user)}


@router.put("/{product_id}")
def update_product_route(product_id: int, payload: ProductUpdatePayload, current_user: dict = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return {"item": update_product(db, product_id, payload, current_user)}


@router.post("/import-xlsx")
async def import_products_xlsx_route(file: UploadFile = File(...), current_user: dict = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return {
        "item": import_products_from_xlsx(
            db,
            content=await file.read(),
            filename=file.filename,
            current_user=current_user,
        )
    }


@router.get("/import-xlsx/{job_id}")
def get_products_import_xlsx_job_route(job_id: str, _: dict = Depends(require_admin)) -> dict:
    return {"item": get_product_import_job(job_id)}