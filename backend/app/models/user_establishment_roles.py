from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

SQL_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")

# Уровень доступа пользователя на конкретном складе. Членство в складе (наличие
# строки) = видимость склада; role = что пользователь может делать с документами
# этого склада: viewer (правит только свои), editor (любые склада), manager
# (+удаление/создание приёмок-инвентаризаций). Удаление документов — всё равно
# только владелец или админ (решение пользователя), независимо от роли склада.
ESTABLISHMENT_ROLES = ("viewer", "editor", "manager")


class UserEstablishmentRole(Base):
    __tablename__ = "user_establishment_roles"
    __table_args__ = (
        UniqueConstraint(
            "user_establishment_role_user_id",
            "user_establishment_role_establishment_id",
            name="uq_user_establishment_role_user_establishment",
        ),
    )

    user_establishment_role_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    user_establishment_role_user_id: Mapped[int] = mapped_column(
        SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_establishment_role_establishment_id: Mapped[int] = mapped_column(
        SQL_ID_TYPE, ForeignKey("establishments.establishment_id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_establishment_role_role: Mapped[str] = mapped_column(String(20), nullable=False)
    user_establishment_role_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    user = relationship("User", back_populates="establishment_roles")
    establishment = relationship("Establishment", back_populates="user_roles")
