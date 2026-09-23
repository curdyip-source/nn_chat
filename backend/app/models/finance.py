from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

SQL_ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (UniqueConstraint("exchange_rate_date", name="uq_exchange_rates_date"),)

    exchange_rate_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    exchange_rate_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # Рублей за 1 USD.
    exchange_rate_value: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    exchange_rate_source: Mapped[str] = mapped_column(String(20), nullable=False, default="cbr", server_default="cbr")
    exchange_rate_fetched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    exchange_rate_updated_by_user_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    exchange_rate_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    updated_by = relationship("User", foreign_keys=[exchange_rate_updated_by_user_id])


class FinanceExpenseCategory(Base):
    __tablename__ = "finance_expense_categories"
    __table_args__ = (UniqueConstraint("finance_expense_category_name", name="uq_finance_expense_categories_name"),)

    finance_expense_category_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    finance_expense_category_name: Mapped[str] = mapped_column(String(255), nullable=False)
    finance_expense_category_owner_user_id: Mapped[int | None] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)
    finance_expense_category_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    owner = relationship("User", foreign_keys=[finance_expense_category_owner_user_id])
    expenses = relationship("FinanceExpense", back_populates="category")


class FinanceExpense(Base):
    __tablename__ = "finance_expenses"

    finance_expense_id: Mapped[int] = mapped_column(SQL_ID_TYPE, primary_key=True, index=True)
    finance_expense_category_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("finance_expense_categories.finance_expense_category_id", ondelete="RESTRICT"), nullable=False, index=True)
    # Точная дата расхода (не месяц!) — фильтр «Финансов» по диапазону дат работает день в день.
    finance_expense_period: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    finance_expense_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    finance_expense_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    finance_expense_owner_user_id: Mapped[int] = mapped_column(SQL_ID_TYPE, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    finance_expense_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    category = relationship("FinanceExpenseCategory", back_populates="expenses")
    owner = relationship("User", foreign_keys=[finance_expense_owner_user_id])
