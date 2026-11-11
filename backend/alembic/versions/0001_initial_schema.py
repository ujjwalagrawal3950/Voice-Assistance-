"""Initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sellers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("marketplace", sa.String(), nullable=False, server_default="mock-marketplace"),
        sa.Column("business_category", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("serviceable_regions", sa.Text(), nullable=True),
        sa.Column("timezone", sa.String(), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("business_goals", sa.Text(), nullable=True),
        sa.Column("target_growth", sa.Float(), nullable=True),
        sa.Column("target_margin", sa.Float(), nullable=True),
        sa.Column("available_replenishment_budget", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("risk_tolerance", sa.String(), nullable=False, server_default="medium"),
        sa.Column("preferred_stock_cover_days", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("storage_capacity", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("seller_id", sa.String(), nullable=False),
        sa.Column("sku_code", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("subcategory", sa.String(), nullable=True),
        sa.Column("selling_price", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Integer(), nullable=False),
        sa.Column("minimum_margin", sa.Float(), nullable=True),
        sa.Column("current_stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved_stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("incoming_stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("supplier_lead_time_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("minimum_order_quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("seasonality_tags", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("seller_id", "sku_code", name="uq_seller_sku_code"),
    )
    op.create_index(op.f("ix_products_seller_id"), "products", ["seller_id"], unique=False)
    op.create_index(op.f("ix_products_category"), "products", ["category"], unique=False)

    op.create_table(
        "calendar_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("event_name", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("geography", sa.String(), nullable=True),
        sa.Column("shopping_lead_in_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("category_relevance", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("confidence", sa.String(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("seller_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("consent", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversations_seller_id"), "conversations", ["seller_id"], unique=False)
    op.create_index(op.f("ix_conversations_session_id"), "conversations", ["session_id"], unique=False)

    op.create_table(
        "daily_performance",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("seller_id", sa.String(), nullable=False),
        sa.Column("sku_id", sa.String(), nullable=False),
        sa.Column("perf_date", sa.Date(), nullable=False),
        sa.Column("units_sold", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gross_sales", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discounts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("net_sales", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("views", sa.Integer(), nullable=True),
        sa.Column("clicks", sa.Integer(), nullable=True),
        sa.Column("orders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conversion_rate", sa.Float(), nullable=True),
        sa.Column("cancellations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("returns", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dispatched_units", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stockout_indicator", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("data_quality", sa.String(), nullable=False, server_default="observed"),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"], ),
        sa.ForeignKeyConstraint(["sku_id"], ["products.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("seller_id", "sku_id", "perf_date", name="uq_seller_sku_date"),
    )
    op.create_index(op.f("ix_daily_performance_seller_id"), "daily_performance", ["seller_id"], unique=False)
    op.create_index(op.f("ix_daily_performance_sku_id"), "daily_performance", ["sku_id"], unique=False)
    op.create_index(op.f("ix_daily_performance_perf_date"), "daily_performance", ["perf_date"], unique=False)

    op.create_table(
        "inventory_snapshots",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("sku_id", sa.String(), nullable=False),
        sa.Column("snapshot_at", sa.DateTime(), nullable=False),
        sa.Column("available_qty", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sold", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("returned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("adjusted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confirmed_incoming_qty", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expected_arrival", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["sku_id"], ["products.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inventory_snapshots_sku_id"), "inventory_snapshots", ["sku_id"], unique=False)
    op.create_index(op.f("ix_inventory_snapshots_snapshot_at"), "inventory_snapshots", ["snapshot_at"], unique=False)

    op.create_table(
        "recommendations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("seller_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("problem_or_opportunity", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("suggested_action", sa.Text(), nullable=False),
        sa.Column("expected_impact", sa.Text(), nullable=True),
        sa.Column("cost_or_budget", sa.Integer(), nullable=True),
        sa.Column("risk", sa.String(), nullable=False, server_default="medium"),
        sa.Column("confidence", sa.String(), nullable=False, server_default="medium"),
        sa.Column("urgency", sa.String(), nullable=False, server_default="medium"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assumptions", sa.Text(), nullable=True),
        sa.Column("what_to_measure_next", sa.Text(), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("approval_status", sa.String(), nullable=False, server_default="new"),
        sa.Column("execution_status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("expiry", sa.Date(), nullable=True),
        sa.Column("related_sku_ids", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recommendations_seller_id"), "recommendations", ["seller_id"], unique=False)


def downgrade() -> None:
    op.drop_table("recommendations")
    op.drop_table("inventory_snapshots")
    op.drop_table("daily_performance")
    op.drop_table("conversations")
    op.drop_table("calendar_events")
    op.drop_table("products")
    op.drop_table("sellers")
