from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

SQL_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class ProductSpec(Base):
    """Характеристики товара (вес, штрихкоды) по НАИМЕНОВАНИЮ.

    Отдельно от products: та таблица — кэш прайса (строки пересоздаются при федерации,
    артикулы меняются), а вес и штрихкоды должны это переживать. Ключ — нормализованное
    наименование (см. product_specs.normalize_product_name); смена написания в прайсе
    сверх нормализации — это новый товар, и это осознанно.
    """

    __tablename__ = "product_specs"

    product_spec_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    product_spec_name_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    product_spec_name: Mapped[str] = mapped_column(String(500), nullable=False)
    # Вес одной штуки, кг.
    product_spec_weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    # На будущее, логики пока нет.
    product_spec_barcode_general: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    product_spec_barcode_secondary: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    product_spec_updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    product_spec_updated_by_user_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
