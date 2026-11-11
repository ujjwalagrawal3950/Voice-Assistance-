"""SQLAlchemy models for the Virtual KAM data model.

Currency is stored as integer paise (INR). Dates are stored as date/time
with explicit timezone handling. All seller-scoped tables carry seller_id
to enforce data isolation at the query layer.
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    desc,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _guid() -> str:
    return str(uuid.uuid4())


class Seller(Base):
    __tablename__ = "sellers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_guid)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    marketplace: Mapped[str] = mapped_column(String, nullable=False, default="mock-marketplace")
    business_category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    serviceable_regions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array as text
    timezone: Mapped[str] = mapped_column(String, nullable=False, default="Asia/Kolkata")
    business_goals: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_growth: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_margin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    available_replenishment_budget: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # paise
    risk_tolerance: Mapped[str] = mapped_column(String, nullable=False, default="medium")  # low/medium/high
    growth_vs_margin_priority: Mapped[str] = mapped_column(String, nullable=False, default="balanced")  # growth/balanced/margin
    supplier_relationship_strength: Mapped[str] = mapped_column(String, nullable=False, default="standard")  # strong/standard/new
    max_credit_stretch_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    preferred_stock_cover_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    storage_capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # units
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    products: Mapped[list["Product"]] = relationship(back_populates="seller", cascade="all, delete-orphan")
    daily_performance: Mapped[list["DailyPerformance"]] = relationship(back_populates="seller", cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="seller", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="seller", cascade="all, delete-orphan")
    proactive_alerts: Mapped[list["ProactiveAlert"]] = relationship(back_populates="seller", cascade="all, delete-orphan")
    conversation_memories: Mapped[list["ConversationMemory"]] = relationship(back_populates="seller", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_guid)
    seller_id: Mapped[str] = mapped_column(String, ForeignKey("sellers.id"), nullable=False, index=True)
    sku_code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    selling_price: Mapped[int] = mapped_column(Integer, nullable=False)  # paise
    unit_cost: Mapped[int] = mapped_column(Integer, nullable=False)  # paise
    minimum_margin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # fraction, e.g. 0.20
    current_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    incoming_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    supplier_lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    minimum_order_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    seasonality_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array as text
    seasonality_tag: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # festival/wedding/payday/evergreen
    demand_segment: Mapped[str] = mapped_column(String, nullable=False, default="discretionary")  # staple/discretionary
    is_festival_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_payday_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_wedding_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    product_attributes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON metadata
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("seller_id", "sku_code", name="uq_seller_sku_code"),
    )

    seller: Mapped["Seller"] = relationship(back_populates="products")
    daily_performance: Mapped[list["DailyPerformance"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    inventory_snapshots: Mapped[list["InventorySnapshot"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class DailyPerformance(Base):
    __tablename__ = "daily_performance"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_guid)
    seller_id: Mapped[str] = mapped_column(String, ForeignKey("sellers.id"), nullable=False, index=True)
    sku_id: Mapped[str] = mapped_column(String, ForeignKey("products.id"), nullable=False, index=True)
    perf_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    units_sold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gross_sales: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # paise
    discounts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # paise
    net_sales: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # paise
    views: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    clicks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversion_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cancellations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    returns: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dispatched_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stockout_indicator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    data_quality: Mapped[str] = mapped_column(String, nullable=False, default="observed")  # observed/estimated/mock
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("seller_id", "sku_id", "perf_date", name="uq_seller_sku_date"),
    )

    seller: Mapped["Seller"] = relationship(back_populates="daily_performance")
    product: Mapped["Product"] = relationship(back_populates="daily_performance")


class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_guid)
    sku_id: Mapped[str] = mapped_column(String, ForeignKey("products.id"), nullable=False, index=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    available_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    returned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    adjusted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confirmed_incoming_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expected_arrival: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    product: Mapped["Product"] = relationship(back_populates="inventory_snapshots")


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_guid)
    event_name: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)  # festival/regional/wedding/sale
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    geography: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # state/region
    shopping_lead_in_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    category_relevance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array as text
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    confidence: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # verified/scenario/estimated
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_guid)
    seller_id: Mapped[str] = mapped_column(String, ForeignKey("sellers.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    problem_or_opportunity: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    suggested_action: Mapped[str] = mapped_column(Text, nullable=False)
    expected_impact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cost_or_budget: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # paise
    risk: Mapped[str] = mapped_column(String, nullable=False, default="medium")  # low/medium/high
    confidence: Mapped[str] = mapped_column(String, nullable=False, default="medium")  # low/medium/high
    urgency: Mapped[str] = mapped_column(String, nullable=False, default="medium")  # low/medium/high
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assumptions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    what_to_measure_next: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    approval_status: Mapped[str] = mapped_column(String, nullable=False, default="new")  # new/viewed/approved/rejected/expired/completed
    execution_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")  # pending/executed/failed
    action_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # restock/cancellation_fix/visibility/pricing/festival_prep
    outcome_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")  # pending/positive/neutral/negative
    outcome_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actual_units_ordered: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_revenue_delta_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_margin_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    outcome_recorded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    related_sku_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array as text
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    seller: Mapped["Seller"] = relationship(back_populates="recommendations")


class ProactiveAlert(Base):
    __tablename__ = "proactive_alerts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_guid)
    seller_id: Mapped[str] = mapped_column(String, ForeignKey("sellers.id"), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String, nullable=False)  # stockout_risk/cancellation_spike/festival_readiness/lost_sales
    severity: Mapped[str] = mapped_column(String, nullable=False, default="medium")  # high/medium/low
    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    spoken_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    related_sku_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    estimated_impact_inr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dismissed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    delivered_channel: Mapped[str] = mapped_column(String, nullable=False, default="in_app")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    seller: Mapped["Seller"] = relationship(back_populates="proactive_alerts")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_guid)
    seller_id: Mapped[str] = mapped_column(String, ForeignKey("sellers.id"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    seller: Mapped["Seller"] = relationship(back_populates="conversations")


class ConversationMemory(Base):
    __tablename__ = "conversation_memories"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_guid)
    seller_id: Mapped[str] = mapped_column(String, ForeignKey("sellers.id"), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    assistant_response: Mapped[str] = mapped_column(Text, nullable=False)
    problem_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    solution_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_takeaway: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    related_sku_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # comma-separated SKU codes
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    seller: Mapped["Seller"] = relationship(back_populates="conversation_memories")


class ChatSession(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True, default=_guid)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.sequence_no",
    )

    __table_args__ = (
        Index("idx_sessions_user_updated", "user_id", desc("updated_at")),
    )


class ChatMessage(Base):
    __tablename__ = "messages"

    message_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String, nullable=False)  # 'user' | 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("idx_messages_session_seq", "session_id", "sequence_no"),
    )
