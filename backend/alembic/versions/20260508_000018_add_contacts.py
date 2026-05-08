"""add contacts

Revision ID: 20260508_000018
Revises: 20260408_000017
Create Date: 2026-05-08 00:00:18

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260508_000018"
down_revision = "20260408_000017"
branch_labels = None
depends_on = None


def _index_names(inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)} if inspector.has_table(table_name) else set()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("contacts"):
        op.create_table(
            "contacts",
            sa.Column("contact_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("contact_type", sa.String(length=50), nullable=False),
            sa.Column("contact_name", sa.String(length=255), nullable=False),
            sa.Column("contact_info", sa.Text(), nullable=True),
            sa.Column("contact_establishment_id", sa.BigInteger(), nullable=True),
            sa.Column("contact_order_method_id", sa.BigInteger(), nullable=True),
            sa.Column("contact_order_sub_method", sa.String(length=255), nullable=True),
            sa.Column("contact_owner_user_id", sa.BigInteger(), nullable=True),
            sa.Column("contact_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["contact_establishment_id"], ["establishments.establishment_id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["contact_order_method_id"], ["order_methods.order_method_id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["contact_owner_user_id"], ["users.user_id"], ondelete="SET NULL"),
        )

    index_names = _index_names(inspector, "contacts")
    if "ix_contacts_contact_id" not in index_names:
        op.create_index("ix_contacts_contact_id", "contacts", ["contact_id"], unique=False)
    if "ix_contacts_contact_type" not in index_names:
        op.create_index("ix_contacts_contact_type", "contacts", ["contact_type"], unique=False)
    if "ix_contacts_contact_name" not in index_names:
        op.create_index("ix_contacts_contact_name", "contacts", ["contact_name"], unique=False)
    if "ix_contacts_contact_establishment_id" not in index_names:
        op.create_index("ix_contacts_contact_establishment_id", "contacts", ["contact_establishment_id"], unique=False)
    if "ix_contacts_contact_order_method_id" not in index_names:
        op.create_index("ix_contacts_contact_order_method_id", "contacts", ["contact_order_method_id"], unique=False)
    if "ix_contacts_contact_owner_user_id" not in index_names:
        op.create_index("ix_contacts_contact_owner_user_id", "contacts", ["contact_owner_user_id"], unique=False)
    if "ix_contacts_contact_created_at" not in index_names:
        op.create_index("ix_contacts_contact_created_at", "contacts", ["contact_created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("contacts"):
        for index_name in [
            "ix_contacts_contact_created_at",
            "ix_contacts_contact_owner_user_id",
            "ix_contacts_contact_order_method_id",
            "ix_contacts_contact_establishment_id",
            "ix_contacts_contact_name",
            "ix_contacts_contact_type",
            "ix_contacts_contact_id",
        ]:
            if index_name in _index_names(inspector, "contacts"):
                op.drop_index(index_name, table_name="contacts")
        op.drop_table("contacts")