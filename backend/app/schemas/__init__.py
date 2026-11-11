"""Pydantic API request/response schemas.

All schemas carry provenance metadata (observed/calculated/forecast/simulated)
and timestamps so the UI can label data status explicitly.
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProvenanceMixin(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    data_status: str = Field(default="observed", description="observed / calculated / estimated / forecast / simulated")
    calculated_at: Optional[datetime] = None


# ── Seller ──────────────────────────────────────────────────────────────

class SellerBase(BaseModel):
    display_name: str
    marketplace: str = "mock-marketplace"
    business_category: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    serviceable_regions: Optional[str] = None
    timezone: str = "Asia/Kolkata"
    business_goals: Optional[str] = None
    target_growth: Optional[float] = None
    target_margin: Optional[float] = None
    available_replenishment_budget: int = 0  # paise
    risk_tolerance: str = "medium"
    growth_vs_margin_priority: str = "balanced"
    supplier_relationship_strength: str = "standard"
    max_credit_stretch_pct: float = 0.0
    preferred_stock_cover_days: int = 14
    storage_capacity: Optional[int] = None


class SellerCreate(SellerBase):
    pass


class SellerUpdate(BaseModel):
    display_name: Optional[str] = None
    business_category: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    serviceable_regions: Optional[str] = None
    timezone: Optional[str] = None
    business_goals: Optional[str] = None
    target_growth: Optional[float] = None
    target_margin: Optional[float] = None
    available_replenishment_budget: Optional[int] = None
    risk_tolerance: Optional[str] = None
    growth_vs_margin_priority: Optional[str] = None
    supplier_relationship_strength: Optional[str] = None
    max_credit_stretch_pct: Optional[float] = None
    preferred_stock_cover_days: Optional[int] = None
    storage_capacity: Optional[int] = None


class SellerResponse(SellerBase):
    id: str
    created_at: datetime
    updated_at: datetime


# ── Dashboard ───────────────────────────────────────────────────────────

class KPIResponse(ProvenanceMixin):
    revenue: int  # paise
    orders: int
    units: int
    average_selling_price: int  # paise
    cancellation_rate: float  # fraction 0-1
    return_rate: float  # fraction 0-1
    conversion_rate: Optional[float] = None
    stockout_sku_count: int
    inventory_value_cost: int  # paise
    inventory_value_selling: int  # paise
    days_of_stock_cover: Optional[float] = None


class DashboardSummary(KPIResponse):
    seller_id: str
    period_start: date
    period_end: date
    comparison_start: date
    comparison_end: date
    revenue_change_pct: Optional[float] = None
    orders_change_pct: Optional[float] = None
    top_alerts: list[str] = Field(default_factory=list)


# ── Product / SKU ───────────────────────────────────────────────────────

class ProductBase(BaseModel):
    sku_code: str
    title: str
    category: str
    subcategory: Optional[str] = None
    selling_price: int  # paise
    unit_cost: int  # paise
    minimum_margin: Optional[float] = None
    current_stock: int = 0
    reserved_stock: int = 0
    incoming_stock: int = 0
    supplier_lead_time_days: int = 7
    minimum_order_quantity: int = 1
    seasonality_tags: Optional[str] = None
    seasonality_tag: Optional[str] = None
    demand_segment: str = "discretionary"
    is_festival_sensitive: bool = False
    is_payday_sensitive: bool = False
    is_wedding_sensitive: bool = False
    product_attributes: Optional[str] = None
    active: bool = True


class ProductCreate(ProductBase):
    seller_id: str


class ProductResponse(ProductBase):
    id: str
    seller_id: str
    created_at: datetime
    updated_at: datetime


class DailyPerformanceResponse(BaseModel):
    id: str
    sku_id: str
    perf_date: date
    units_sold: int
    gross_sales: int  # paise
    net_sales: int  # paise
    views: Optional[int] = None
    clicks: Optional[int] = None
    orders: int
    conversion_rate: Optional[float] = None
    cancellations: int
    returns: int
    stockout_indicator: bool
    data_status: str = "observed"


# ── Recommendation ──────────────────────────────────────────────────────

class RecommendationBase(BaseModel):
    title: str
    problem_or_opportunity: str
    evidence: Optional[str] = None
    suggested_action: str
    expected_impact: Optional[str] = None
    cost_or_budget: Optional[int] = None  # paise
    risk: str = "medium"
    confidence: str = "medium"
    urgency: str = "medium"
    priority: int = 0
    assumptions: Optional[str] = None
    what_to_measure_next: Optional[str] = None
    requires_approval: bool = True
    expiry: Optional[date] = None
    related_sku_ids: Optional[str] = None


class RecommendationCreate(RecommendationBase):
    seller_id: str


class RecommendationResponse(RecommendationBase):
    id: str
    seller_id: str
    approval_status: str
    execution_status: str
    action_type: Optional[str] = None
    outcome_status: str = "pending"
    outcome_notes: Optional[str] = None
    actual_units_ordered: Optional[int] = None
    actual_revenue_delta_pct: Optional[float] = None
    actual_margin_pct: Optional[float] = None
    outcome_recorded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ApprovalAction(BaseModel):
    action: str  # "approve" or "reject"
    notes: Optional[str] = None


class OutcomeRecord(BaseModel):
    outcome_status: str  # "positive" | "neutral" | "negative"
    actual_units_ordered: Optional[int] = None
    actual_revenue_delta_pct: Optional[float] = None
    actual_margin_pct: Optional[float] = None
    outcome_notes: Optional[str] = None


class ProactiveAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    seller_id: str
    alert_type: str
    severity: str
    title: str
    message: str
    spoken_message: Optional[str] = None
    related_sku_id: Optional[str] = None
    estimated_impact_inr: Optional[int] = None
    is_read: bool
    dismissed: bool
    delivered_channel: str
    created_at: datetime


class WhatIfRequest(BaseModel):
    budget_inr: float = Field(default=15000.0, gt=0)
    sku_id: Optional[str] = None
    delay_days: int = Field(default=7, ge=0, le=60)
    festival_uplift_pct: float = Field(default=25.0, ge=0.0, le=200.0)


# ── Chat / Agent ────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    channel: str = "text"  # text | voice
    conversation_id: Optional[str] = None
    locale: Optional[str] = "en-IN"


class ChatResponse(BaseModel):
    response_text: str
    spoken_text: Optional[str] = None
    conversation_id: str
    findings: Optional[list[str]] = None
    recommendation_ids: list[str] = Field(default_factory=list)
    follow_up_question: Optional[str] = None
    tool_activity: Optional[list[str]] = None
    specialists_consulted: Optional[list[str]] = None


# ── ChatGPT-style Sessions Sidebar ──────────────────────────────────────

class CreateSessionRequest(BaseModel):
    first_message: str = Field(..., min_length=1)


class CreateSessionResponse(BaseModel):
    session_id: str
    title: str


class SessionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    session_id: str
    title: Optional[str] = None
    updated_at: datetime


class SessionMessageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role: str
    content: str
    sequence_no: int
