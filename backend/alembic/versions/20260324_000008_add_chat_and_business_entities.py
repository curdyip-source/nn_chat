"""add chat and business entities

Revision ID: 20260324_000008
Revises: 20260323_000007
Create Date: 2026-03-24 00:00:08

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260324_000008"
down_revision = "20260323_000007"
branch_labels = None
depends_on = None


def _index_names(inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)} if inspector.has_table(table_name) else set()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("users"):
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "user_profile_photo" not in user_columns:
            op.add_column("users", sa.Column("user_profile_photo", sa.Text(), nullable=True))
        if "user_verified_user_id" not in user_columns:
            op.add_column("users", sa.Column("user_verified_user_id", sa.BigInteger(), nullable=True))
            op.create_foreign_key("fk_users_user_verified_user_id_users", "users", "users", ["user_verified_user_id"], ["user_id"], ondelete="SET NULL")
        user_indexes = _index_names(inspector, "users")
        if "ix_users_user_verified_user_id" not in user_indexes:
            op.create_index("ix_users_user_verified_user_id", "users", ["user_verified_user_id"], unique=False)

    if not inspector.has_table("establishments"):
        op.create_table(
            "establishments",
            sa.Column("establishment_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("establishment_name", sa.String(length=255), nullable=False),
            sa.Column("establishment_address", sa.Text(), nullable=True),
            sa.Column("establishment_owner_user_id", sa.BigInteger(), nullable=True),
            sa.Column("establishment_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["establishment_owner_user_id"], ["users.user_id"], ondelete="SET NULL"),
            sa.UniqueConstraint("establishment_name", name="uq_establishments_name"),
        )
        op.create_index("ix_establishments_establishment_id", "establishments", ["establishment_id"], unique=False)
        op.create_index("ix_establishments_establishment_owner_user_id", "establishments", ["establishment_owner_user_id"], unique=False)

    if not inspector.has_table("order_methods"):
        op.create_table(
            "order_methods",
            sa.Column("order_method_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("order_method_name", sa.String(length=255), nullable=False),
            sa.Column("order_method_owner_user_id", sa.BigInteger(), nullable=True),
            sa.Column("order_method_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["order_method_owner_user_id"], ["users.user_id"], ondelete="SET NULL"),
            sa.UniqueConstraint("order_method_name", name="uq_order_methods_name"),
        )
        op.create_index("ix_order_methods_order_method_id", "order_methods", ["order_method_id"], unique=False)
        op.create_index("ix_order_methods_order_method_owner_user_id", "order_methods", ["order_method_owner_user_id"], unique=False)

    if not inspector.has_table("statuses"):
        op.create_table(
            "statuses",
            sa.Column("status_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("status_type", sa.String(length=100), nullable=False),
            sa.Column("status_status", sa.String(length=255), nullable=False),
            sa.Column("status_color", sa.String(length=50), nullable=True),
            sa.Column("status_owner_user_id", sa.BigInteger(), nullable=True),
            sa.Column("status_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["status_owner_user_id"], ["users.user_id"], ondelete="SET NULL"),
        )
        op.create_index("ix_statuses_status_id", "statuses", ["status_id"], unique=False)
        op.create_index("ix_statuses_status_type", "statuses", ["status_type"], unique=False)
        op.create_index("ix_statuses_status_owner_user_id", "statuses", ["status_owner_user_id"], unique=False)

    if not inspector.has_table("currencies"):
        op.create_table(
            "currencies",
            sa.Column("currency_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("currency_name", sa.String(length=100), nullable=False),
            sa.Column("currency_sign", sa.String(length=20), nullable=True),
            sa.Column("currency_owner_user_id", sa.BigInteger(), nullable=True),
            sa.Column("currency_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["currency_owner_user_id"], ["users.user_id"], ondelete="SET NULL"),
            sa.UniqueConstraint("currency_name", name="uq_currencies_name"),
        )
        op.create_index("ix_currencies_currency_id", "currencies", ["currency_id"], unique=False)
        op.create_index("ix_currencies_currency_owner_user_id", "currencies", ["currency_owner_user_id"], unique=False)

    if not inspector.has_table("products"):
        op.create_table(
            "products",
            sa.Column("product_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("product_article", sa.String(length=100), nullable=False),
            sa.Column("product_name", sa.String(length=500), nullable=False),
            sa.Column("product_cost_usd", sa.Numeric(12, 2), nullable=False),
            sa.Column("product_owner_user_id", sa.BigInteger(), nullable=True),
            sa.Column("product_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["product_owner_user_id"], ["users.user_id"], ondelete="SET NULL"),
            sa.UniqueConstraint("product_article", name="uq_products_article"),
        )
        op.create_index("ix_products_product_id", "products", ["product_id"], unique=False)
        op.create_index("ix_products_product_article", "products", ["product_article"], unique=False)
        op.create_index("ix_products_product_name", "products", ["product_name"], unique=False)
        op.create_index("ix_products_product_owner_user_id", "products", ["product_owner_user_id"], unique=False)

    if not inspector.has_table("orders"):
        op.create_table(
            "orders",
            sa.Column("order_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("order_establishment_id", sa.BigInteger(), nullable=False),
            sa.Column("order_method_id", sa.BigInteger(), nullable=False),
            sa.Column("order_customer", sa.String(length=255), nullable=False),
            sa.Column("order_info", sa.Text(), nullable=False),
            sa.Column("order_status_id", sa.BigInteger(), nullable=False),
            sa.Column("order_owner_user_id", sa.BigInteger(), nullable=False),
            sa.Column("order_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["order_establishment_id"], ["establishments.establishment_id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["order_method_id"], ["order_methods.order_method_id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["order_status_id"], ["statuses.status_id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["order_owner_user_id"], ["users.user_id"], ondelete="CASCADE"),
        )
        op.create_index("ix_orders_order_id", "orders", ["order_id"], unique=False)
        op.create_index("ix_orders_order_establishment_id", "orders", ["order_establishment_id"], unique=False)
        op.create_index("ix_orders_order_method_id", "orders", ["order_method_id"], unique=False)
        op.create_index("ix_orders_order_status_id", "orders", ["order_status_id"], unique=False)
        op.create_index("ix_orders_order_owner_user_id", "orders", ["order_owner_user_id"], unique=False)
        op.create_index("ix_orders_order_created_at", "orders", ["order_created_at"], unique=False)

    if not inspector.has_table("inventories"):
        op.create_table(
            "inventories",
            sa.Column("inventory_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("inventory_establishment_id", sa.BigInteger(), nullable=False),
            sa.Column("inventory_status_id", sa.BigInteger(), nullable=False),
            sa.Column("inventory_owner_user_id", sa.BigInteger(), nullable=False),
            sa.Column("inventory_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["inventory_establishment_id"], ["establishments.establishment_id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["inventory_status_id"], ["statuses.status_id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["inventory_owner_user_id"], ["users.user_id"], ondelete="CASCADE"),
        )
        op.create_index("ix_inventories_inventory_id", "inventories", ["inventory_id"], unique=False)
        op.create_index("ix_inventories_inventory_establishment_id", "inventories", ["inventory_establishment_id"], unique=False)
        op.create_index("ix_inventories_inventory_status_id", "inventories", ["inventory_status_id"], unique=False)
        op.create_index("ix_inventories_inventory_owner_user_id", "inventories", ["inventory_owner_user_id"], unique=False)
        op.create_index("ix_inventories_inventory_created_at", "inventories", ["inventory_created_at"], unique=False)

    if not inspector.has_table("product_registrations"):
        op.create_table(
            "product_registrations",
            sa.Column("product_registration_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("product_registration_establishment_id", sa.BigInteger(), nullable=False),
            sa.Column("product_registration_status_id", sa.BigInteger(), nullable=False),
            sa.Column("product_registration_owner_user_id", sa.BigInteger(), nullable=False),
            sa.Column("product_registration_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["product_registration_establishment_id"], ["establishments.establishment_id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["product_registration_status_id"], ["statuses.status_id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["product_registration_owner_user_id"], ["users.user_id"], ondelete="CASCADE"),
        )
        op.create_index("ix_prod_regs_id", "product_registrations", ["product_registration_id"], unique=False)
        op.create_index("ix_prod_regs_est_id", "product_registrations", ["product_registration_establishment_id"], unique=False)
        op.create_index("ix_prod_regs_status_id", "product_registrations", ["product_registration_status_id"], unique=False)
        op.create_index("ix_prod_regs_owner_id", "product_registrations", ["product_registration_owner_user_id"], unique=False)
        op.create_index("ix_prod_regs_created_at", "product_registrations", ["product_registration_created_at"], unique=False)

    if not inspector.has_table("order_items"):
        op.create_table(
            "order_items",
            sa.Column("order_item_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("order_item_order_id", sa.BigInteger(), nullable=False),
            sa.Column("order_item_product_id", sa.BigInteger(), nullable=True),
            sa.Column("order_item_name", sa.String(length=500), nullable=False),
            sa.Column("order_item_article", sa.String(length=100), nullable=True),
            sa.Column("order_item_quantity", sa.Integer(), nullable=False),
            sa.Column("order_item_price", sa.Numeric(12, 2), nullable=False),
            sa.Column("order_item_currency_id", sa.BigInteger(), nullable=True),
            sa.Column("order_item_owner_user_id", sa.BigInteger(), nullable=False),
            sa.Column("order_item_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["order_item_order_id"], ["orders.order_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["order_item_product_id"], ["products.product_id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["order_item_currency_id"], ["currencies.currency_id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["order_item_owner_user_id"], ["users.user_id"], ondelete="CASCADE"),
        )
        op.create_index("ix_order_items_order_item_id", "order_items", ["order_item_id"], unique=False)
        op.create_index("ix_order_items_order_item_order_id", "order_items", ["order_item_order_id"], unique=False)
        op.create_index("ix_order_items_order_item_product_id", "order_items", ["order_item_product_id"], unique=False)
        op.create_index("ix_order_items_order_item_currency_id", "order_items", ["order_item_currency_id"], unique=False)
        op.create_index("ix_order_items_order_item_owner_user_id", "order_items", ["order_item_owner_user_id"], unique=False)

    if not inspector.has_table("order_comments"):
        op.create_table(
            "order_comments",
            sa.Column("order_comment_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("order_comment_order_id", sa.BigInteger(), nullable=False),
            sa.Column("order_comment_text", sa.Text(), nullable=False),
            sa.Column("order_comment_owner_user_id", sa.BigInteger(), nullable=False),
            sa.Column("order_comment_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["order_comment_order_id"], ["orders.order_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["order_comment_owner_user_id"], ["users.user_id"], ondelete="CASCADE"),
        )
        op.create_index("ix_order_comments_order_comment_id", "order_comments", ["order_comment_id"], unique=False)
        op.create_index("ix_order_comments_order_comment_order_id", "order_comments", ["order_comment_order_id"], unique=False)
        op.create_index("ix_order_comments_order_comment_owner_user_id", "order_comments", ["order_comment_owner_user_id"], unique=False)

    if not inspector.has_table("inventory_items"):
        op.create_table(
            "inventory_items",
            sa.Column("inventory_item_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("inventory_item_inventory_id", sa.BigInteger(), nullable=False),
            sa.Column("inventory_item_product_id", sa.BigInteger(), nullable=True),
            sa.Column("inventory_item_name", sa.String(length=500), nullable=False),
            sa.Column("inventory_item_article", sa.String(length=100), nullable=True),
            sa.Column("inventory_item_quantity", sa.Integer(), nullable=False),
            sa.Column("inventory_item_cost", sa.Numeric(12, 2), nullable=False),
            sa.Column("inventory_item_currency_id", sa.BigInteger(), nullable=True),
            sa.Column("inventory_item_owner_user_id", sa.BigInteger(), nullable=False),
            sa.Column("inventory_item_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["inventory_item_inventory_id"], ["inventories.inventory_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["inventory_item_product_id"], ["products.product_id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["inventory_item_currency_id"], ["currencies.currency_id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["inventory_item_owner_user_id"], ["users.user_id"], ondelete="CASCADE"),
        )
        op.create_index("ix_inventory_items_inventory_item_id", "inventory_items", ["inventory_item_id"], unique=False)
        op.create_index("ix_inventory_items_inventory_item_inventory_id", "inventory_items", ["inventory_item_inventory_id"], unique=False)
        op.create_index("ix_inventory_items_inventory_item_product_id", "inventory_items", ["inventory_item_product_id"], unique=False)
        op.create_index("ix_inventory_items_inventory_item_currency_id", "inventory_items", ["inventory_item_currency_id"], unique=False)
        op.create_index("ix_inventory_items_inventory_item_owner_user_id", "inventory_items", ["inventory_item_owner_user_id"], unique=False)

    if not inspector.has_table("product_registration_items"):
        op.create_table(
            "product_registration_items",
            sa.Column("product_registration_item_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("product_registration_item_product_registration_id", sa.BigInteger(), nullable=False),
            sa.Column("product_registration_item_product_id", sa.BigInteger(), nullable=True),
            sa.Column("product_registration_item_name", sa.String(length=500), nullable=False),
            sa.Column("product_registration_item_article", sa.String(length=100), nullable=True),
            sa.Column("product_registration_item_quantity", sa.Integer(), nullable=False),
            sa.Column("product_registration_item_cost", sa.Numeric(12, 2), nullable=False),
            sa.Column("product_registration_item_currency_id", sa.BigInteger(), nullable=True),
            sa.Column("product_registration_item_owner_user_id", sa.BigInteger(), nullable=False),
            sa.Column("product_registration_item_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["product_registration_item_product_registration_id"], ["product_registrations.product_registration_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["product_registration_item_product_id"], ["products.product_id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["product_registration_item_currency_id"], ["currencies.currency_id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["product_registration_item_owner_user_id"], ["users.user_id"], ondelete="CASCADE"),
        )
        op.create_index("ix_prod_reg_items_id", "product_registration_items", ["product_registration_item_id"], unique=False)
        op.create_index("ix_prod_reg_items_reg_id", "product_registration_items", ["product_registration_item_product_registration_id"], unique=False)
        op.create_index("ix_prod_reg_items_product_id", "product_registration_items", ["product_registration_item_product_id"], unique=False)
        op.create_index("ix_prod_reg_items_currency_id", "product_registration_items", ["product_registration_item_currency_id"], unique=False)
        op.create_index("ix_prod_reg_items_owner_id", "product_registration_items", ["product_registration_item_owner_user_id"], unique=False)

    if not inspector.has_table("messages"):
        op.create_table(
            "messages",
            sa.Column("message_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("message_type", sa.String(length=50), nullable=False),
            sa.Column("message_text", sa.Text(), nullable=True),
            sa.Column("message_owner_user_id", sa.BigInteger(), nullable=False),
            sa.Column("message_order_id", sa.BigInteger(), nullable=True),
            sa.Column("message_inventory_id", sa.BigInteger(), nullable=True),
            sa.Column("message_product_registration_id", sa.BigInteger(), nullable=True),
            sa.Column("message_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["message_owner_user_id"], ["users.user_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["message_order_id"], ["orders.order_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["message_inventory_id"], ["inventories.inventory_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["message_product_registration_id"], ["product_registrations.product_registration_id"], ondelete="CASCADE"),
        )
        op.create_index("ix_messages_message_id", "messages", ["message_id"], unique=False)
        op.create_index("ix_messages_message_type", "messages", ["message_type"], unique=False)
        op.create_index("ix_messages_message_owner_user_id", "messages", ["message_owner_user_id"], unique=False)
        op.create_index("ix_messages_message_order_id", "messages", ["message_order_id"], unique=False)
        op.create_index("ix_messages_message_inventory_id", "messages", ["message_inventory_id"], unique=False)
        op.create_index("ix_messages_message_product_registration_id", "messages", ["message_product_registration_id"], unique=False)
        op.create_index("ix_messages_message_created_at", "messages", ["message_created_at"], unique=False)

    if not inspector.has_table("message_attachments"):
        op.create_table(
            "message_attachments",
            sa.Column("attachment_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("attachment_message_id", sa.BigInteger(), nullable=False),
            sa.Column("attachment_owner_user_id", sa.BigInteger(), nullable=False),
            sa.Column("attachment_kind", sa.String(length=50), nullable=False),
            sa.Column("attachment_original_filename", sa.String(length=255), nullable=False),
            sa.Column("attachment_mime_type", sa.String(length=150), nullable=False),
            sa.Column("attachment_storage_key", sa.String(length=255), nullable=False),
            sa.Column("attachment_size_bytes", sa.Integer(), nullable=True),
            sa.Column("attachment_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["attachment_message_id"], ["messages.message_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["attachment_owner_user_id"], ["users.user_id"], ondelete="CASCADE"),
            sa.UniqueConstraint("attachment_storage_key", name="uq_message_attachments_storage_key"),
        )
        op.create_index("ix_message_attachments_attachment_id", "message_attachments", ["attachment_id"], unique=False)
        op.create_index("ix_message_attachments_attachment_message_id", "message_attachments", ["attachment_message_id"], unique=False)
        op.create_index("ix_message_attachments_attachment_owner_user_id", "message_attachments", ["attachment_owner_user_id"], unique=False)

    if not inspector.has_table("user_devices"):
        op.create_table(
            "user_devices",
            sa.Column("user_device_id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("user_device_user_id", sa.BigInteger(), nullable=False),
            sa.Column("user_device_token", sa.String(length=255), nullable=False),
            sa.Column("user_device_platform", sa.String(length=50), nullable=False),
            sa.Column("user_device_is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("user_device_created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("user_device_updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["user_device_user_id"], ["users.user_id"], ondelete="CASCADE"),
            sa.UniqueConstraint("user_device_token", name="uq_user_devices_token"),
        )
        op.create_index("ix_user_devices_user_device_id", "user_devices", ["user_device_id"], unique=False)
        op.create_index("ix_user_devices_user_device_user_id", "user_devices", ["user_device_user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    for table_name, indexes in [
        ("user_devices", ["ix_user_devices_user_device_user_id", "ix_user_devices_user_device_id"]),
        ("message_attachments", ["ix_message_attachments_attachment_owner_user_id", "ix_message_attachments_attachment_message_id", "ix_message_attachments_attachment_id"]),
        ("messages", ["ix_messages_message_created_at", "ix_messages_message_product_registration_id", "ix_messages_message_inventory_id", "ix_messages_message_order_id", "ix_messages_message_owner_user_id", "ix_messages_message_type", "ix_messages_message_id"]),
        ("product_registration_items", ["ix_prod_reg_items_owner_id", "ix_prod_reg_items_currency_id", "ix_prod_reg_items_product_id", "ix_prod_reg_items_reg_id", "ix_prod_reg_items_id"]),
        ("inventory_items", ["ix_inventory_items_inventory_item_owner_user_id", "ix_inventory_items_inventory_item_currency_id", "ix_inventory_items_inventory_item_product_id", "ix_inventory_items_inventory_item_inventory_id", "ix_inventory_items_inventory_item_id"]),
        ("order_comments", ["ix_order_comments_order_comment_owner_user_id", "ix_order_comments_order_comment_order_id", "ix_order_comments_order_comment_id"]),
        ("order_items", ["ix_order_items_order_item_owner_user_id", "ix_order_items_order_item_currency_id", "ix_order_items_order_item_product_id", "ix_order_items_order_item_order_id", "ix_order_items_order_item_id"]),
        ("product_registrations", ["ix_prod_regs_created_at", "ix_prod_regs_owner_id", "ix_prod_regs_status_id", "ix_prod_regs_est_id", "ix_prod_regs_id"]),
        ("inventories", ["ix_inventories_inventory_created_at", "ix_inventories_inventory_owner_user_id", "ix_inventories_inventory_status_id", "ix_inventories_inventory_establishment_id", "ix_inventories_inventory_id"]),
        ("orders", ["ix_orders_order_created_at", "ix_orders_order_owner_user_id", "ix_orders_order_status_id", "ix_orders_order_method_id", "ix_orders_order_establishment_id", "ix_orders_order_id"]),
        ("products", ["ix_products_product_owner_user_id", "ix_products_product_name", "ix_products_product_article", "ix_products_product_id"]),
        ("currencies", ["ix_currencies_currency_owner_user_id", "ix_currencies_currency_id"]),
        ("statuses", ["ix_statuses_status_owner_user_id", "ix_statuses_status_type", "ix_statuses_status_id"]),
        ("order_methods", ["ix_order_methods_order_method_owner_user_id", "ix_order_methods_order_method_id"]),
        ("establishments", ["ix_establishments_establishment_owner_user_id", "ix_establishments_establishment_id"]),
    ]:
        if inspector.has_table(table_name):
            table_indexes = _index_names(inspector, table_name)
            for index_name in indexes:
                if index_name in table_indexes:
                    op.drop_index(index_name, table_name=table_name)
            op.drop_table(table_name)

    if inspector.has_table("users"):
        user_indexes = _index_names(inspector, "users")
        if "ix_users_user_verified_user_id" in user_indexes:
            op.drop_index("ix_users_user_verified_user_id", table_name="users")
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("users")}
        if "fk_users_user_verified_user_id_users" in foreign_keys:
            op.drop_constraint("fk_users_user_verified_user_id_users", "users", type_="foreignkey")
        if "user_verified_user_id" in user_columns:
            op.drop_column("users", "user_verified_user_id")
        if "user_profile_photo" in user_columns:
            op.drop_column("users", "user_profile_photo")