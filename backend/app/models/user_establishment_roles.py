from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

SQL_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")

# Членство пользователя в складе + его настройки прав НА ЭТОМ складе (per-warehouse):
# view/edit/delete scope и can_create. scope: own = только свои документы этого склада;
# establishment = любые документы этого склада. У пользователя может быть разный набор
# на разных складах (напр. менеджер на Белке, просмотр на Туле).


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
    # Настройки прав на этом складе. scope: own | establishment (для view/edit/delete).
    user_establishment_role_view_scope: Mapped[str] = mapped_column(String(20), nullable=False, default="establishment", server_default="establishment")
    user_establishment_role_can_create: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=func.false())
    user_establishment_role_edit_scope: Mapped[str] = mapped_column(String(20), nullable=False, default="none", server_default="none")
    user_establishment_role_delete_scope: Mapped[str] = mapped_column(String(20), nullable=False, default="none", server_default="none")
    user_establishment_role_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    user = relationship("User", back_populates="establishment_roles")
    establishment = relationship("Establishment", back_populates="user_roles")
