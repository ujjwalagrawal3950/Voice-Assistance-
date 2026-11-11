"""Typed tools for the Virtual KAM agent.

Each tool has a typed input/output schema, seller-scoped permission checks,
and clear error behaviour. The LLM calls these tools for current business facts;
it never calculates KPIs or invents data.
"""

from datetime import date, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.api.deps import get_current_seller_id
from app.database import SessionLocal
from app.models import (
    CalendarEvent,
    DailyPerformance,
    Product,
    Recommendation,
    Seller,
)
from app.services.intelligence import (
    build_smart_replenishment_plan as _build_smart_replenishment_plan,
    calculate_stockout_impact as _calculate_stockout_impact,
    decompose_revenue_change as _decompose_revenue_change,
    generate_proactive_alerts as _generate_proactive_alerts,
    get_outcome_track_record as _get_outcome_track_record,
    simulate_what_if_scenario as _simulate_what_if_scenario,
)
from app.services.kpi import (
    calculate_average_selling_price,
    calculate_cancellation_rate,
    calculate_conversion_rate,
    calculate_gross_sales,
    calculate_inventory_value,
    calculate_net_sales,
    calculate_orders,
    calculate_return_rate,
    calculate_stock_cover_days,
    calculate_stockout_sku_count,
    calculate_units_sold,
    period_over_period_change,
)


class ToolError(Exception):
    """Raised when a tool cannot complete its work."""


def _get_db() -> Session:
    return SessionLocal()


def _get_seller(db: Session, seller_id: str) -> Optional[Seller]:
    return db.query(Seller).filter(Seller.id == seller_id).first()


# ── Tool: get_seller_profile ────────────────────────────────────────────

def get_seller_profile(seller_id: str) -> dict[str, Any]:
    """Return the authenticated seller's profile and business constraints."""
    db = _get_db()
    try:
        seller = _get_seller(db, seller_id)
        if not seller:
            raise ToolError(f"Seller {seller_id} not found")
        return {
            "id": seller.id,
            "display_name": seller.display_name,
            "marketplace": seller.marketplace,
            "business_category": seller.business_category,
            "state": seller.state,
            "city": seller.city,
            "timezone": seller.timezone,
            "business_goals": seller.business_goals,
            "target_growth": seller.target_growth,
            "target_margin": seller.target_margin,
            "available_replenishment_budget": seller.available_replenishment_budget,
            "risk_tolerance": seller.risk_tolerance,
            "growth_vs_margin_priority": getattr(seller, "growth_vs_margin_priority", "balanced"),
            "supplier_relationship_strength": getattr(seller, "supplier_relationship_strength", "standard"),
            "max_credit_stretch_pct": getattr(seller, "max_credit_stretch_pct", 0.0),
            "preferred_stock_cover_days": seller.preferred_stock_cover_days,
            "storage_capacity": seller.storage_capacity,
        }
    finally:
        db.close()


# ── Tool: get_dashboard_kpis ────────────────────────────────────────────

def get_dashboard_kpis(seller_id: str, period_days: int = 30) -> dict[str, Any]:
    """Return current-period KPIs with period-over-period change."""
    db = _get_db()
    try:
        today = date.today()
        period_end = today
        comparison_end = today - timedelta(days=period_days)

        revenue = calculate_gross_sales(db, seller_id, period_end, period_days)
        orders = calculate_orders(db, seller_id, period_end, period_days)
        units = calculate_units_sold(db, seller_id, period_end, period_days)
        asp = calculate_average_selling_price(db, seller_id, period_end, period_days)
        cancellation = calculate_cancellation_rate(db, seller_id, period_end, period_days)
        returns = calculate_return_rate(db, seller_id, period_end, period_days)
        conversion = calculate_conversion_rate(db, seller_id, period_end, period_days)
        stockouts = calculate_stockout_sku_count(db, seller_id, as_of=period_end)
        inventory = calculate_inventory_value(db, seller_id)

        prev_revenue = calculate_gross_sales(db, seller_id, comparison_end, period_days)
        prev_orders = calculate_orders(db, seller_id, comparison_end, period_days)
        prev_asp = calculate_average_selling_price(db, seller_id, comparison_end, period_days)
        prev_cancellation = calculate_cancellation_rate(db, seller_id, comparison_end, period_days)
        prev_conversion = calculate_conversion_rate(db, seller_id, comparison_end, period_days)

        # Count SKUs marked stocked out in the comparison period and total views change
        comp_start = comparison_end - timedelta(days=period_days - 1)
        curr_start = period_end - timedelta(days=period_days - 1)
        prev_rows = (
            db.query(DailyPerformance)
            .filter(
                DailyPerformance.seller_id == seller_id,
                DailyPerformance.perf_date >= comp_start,
                DailyPerformance.perf_date <= comparison_end,
            )
            .all()
        )
        curr_rows = (
            db.query(DailyPerformance)
            .filter(
                DailyPerformance.seller_id == seller_id,
                DailyPerformance.perf_date >= curr_start,
                DailyPerformance.perf_date <= period_end,
            )
            .all()
        )
        prev_stockout_skus = len({r.sku_id for r in prev_rows if r.stockout_indicator})
        prev_views = sum(r.views or 0 for r in prev_rows)
        curr_views = sum(r.views or 0 for r in curr_rows)
        views_change = period_over_period_change(curr_views, prev_views)

        return {
            "seller_id": seller_id,
            "period_days": period_days,
            "revenue": revenue["value"],
            "orders": orders["value"],
            "units": units["value"],
            "average_selling_price": asp["value"],
            "cancellation_rate": cancellation["value"],
            "return_rate": returns["value"],
            "conversion_rate": conversion["value"],
            "stockout_sku_count": stockouts["value"],
            "inventory_value_cost": inventory["value_at_cost"],
            "inventory_value_selling": inventory["value_at_selling"],
            "revenue_change_pct": period_over_period_change(
                revenue["value"], prev_revenue["value"]
            ),
            "orders_change_pct": period_over_period_change(
                orders["value"], prev_orders["value"]
            ),
            "views_change_pct": views_change,
            "this_month": {
                "sales_inr": round(revenue["value"] / 100, 2),
                "orders": orders["value"],
                "cancellation_rate_pct": round((cancellation["value"] or 0) * 100, 1),
                "average_selling_price_inr": round((asp["value"] or 0) / 100, 2),
                "out_of_stock_products": stockouts["value"],
                "views": curr_views,
            },
            "last_month": {
                "sales_inr": round(prev_revenue["value"] / 100, 2),
                "orders": prev_orders["value"],
                "cancellation_rate_pct": round((prev_cancellation["value"] or 0) * 100, 1),
                "average_selling_price_inr": round((prev_asp["value"] or 0) / 100, 2),
                "out_of_stock_products": prev_stockout_skus,
                "views": prev_views,
            },
            "data_status": "calculated",
        }
    finally:
        db.close()


# ── Tool: get_sales_trend ───────────────────────────────────────────────

def get_sales_trend(seller_id: str, period_days: int = 30) -> dict[str, Any]:
    """Return daily net sales for the period, for trend visualization."""
    db = _get_db()
    try:
        today = date.today()
        start = today - timedelta(days=period_days - 1)
        rows = (
            db.query(DailyPerformance)
            .filter(
                DailyPerformance.seller_id == seller_id,
                DailyPerformance.perf_date >= start,
                DailyPerformance.perf_date <= today,
            )
            .order_by(DailyPerformance.perf_date)
            .all()
        )
        trend = [
            {
                "date": r.perf_date.isoformat(),
                "net_sales": r.net_sales,
                "orders": r.orders,
                "units_sold": r.units_sold,
                "stockout": r.stockout_indicator,
            }
            for r in rows
        ]
        return {"seller_id": seller_id, "period_days": period_days, "trend": trend}
    finally:
        db.close()


# ── Tool: get_sku_performance ───────────────────────────────────────────

def get_sku_performance(seller_id: str, sku_id: str) -> dict[str, Any]:
    """Return a single SKU's current performance, stock, and cover."""
    db = _get_db()
    try:
        product = (
            db.query(Product)
            .filter(Product.id == sku_id, Product.seller_id == seller_id)
            .first()
        )
        if not product:
            raise ToolError(f"SKU {sku_id} not found for seller {seller_id}")

        today = date.today()
        cover = calculate_stock_cover_days(db, seller_id, sku_id, today, days=30)

        # Last 7 days sales
        start = today - timedelta(days=6)
        rows = (
            db.query(DailyPerformance)
            .filter(
                DailyPerformance.seller_id == seller_id,
                DailyPerformance.sku_id == sku_id,
                DailyPerformance.perf_date >= start,
                DailyPerformance.perf_date <= today,
            )
            .all()
        )
        recent_units = sum(r.units_sold for r in rows)
        recent_net = sum(r.net_sales for r in rows)
        recent_cancellations = sum(r.cancellations for r in rows)

        return {
            "sku_id": sku_id,
            "sku_code": product.sku_code,
            "title": product.title,
            "category": product.category,
            "selling_price": product.selling_price,
            "unit_cost": product.unit_cost,
            "current_stock": product.current_stock,
            "reserved_stock": product.reserved_stock,
            "incoming_stock": product.incoming_stock,
            "supplier_lead_time_days": product.supplier_lead_time_days,
            "minimum_order_quantity": product.minimum_order_quantity,
            "days_of_stock_cover": cover["value"],
            "recent_7d_units": recent_units,
            "recent_7d_net_sales": recent_net,
            "recent_7d_cancellations": recent_cancellations,
            "is_stockout": product.current_stock <= 0,
            "data_status": "observed",
        }
    finally:
        db.close()


# ── Tool: get_inventory_health ──────────────────────────────────────────

def get_inventory_health(seller_id: str) -> dict[str, Any]:
    """Return inventory health: stockouts, low cover, dead stock candidates."""
    db = _get_db()
    try:
        today = date.today()
        products = (
            db.query(Product)
            .filter(Product.seller_id == seller_id, Product.active == True)  # noqa: E712
            .all()
        )

        stockouts = []
        low_cover = []
        dead_stock = []

        for p in products:
            cover = calculate_stock_cover_days(db, seller_id, p.id, today, days=30)
            if p.current_stock <= 0:
                stockouts.append(
                    {
                        "sku_id": p.id,
                        "sku_code": p.sku_code,
                        "title": p.title,
                        "category": p.category,
                    }
                )
            elif cover["value"] is not None and cover["value"] < 7:
                low_cover.append(
                    {
                        "sku_id": p.id,
                        "sku_code": p.sku_code,
                        "title": p.title,
                        "cover_days": cover["value"],
                    }
                )
            # Dead stock: high stock + no recent sales + not incoming
            if (
                p.current_stock > 100
                and p.incoming_stock == 0
                and cover["value"] is not None
                and cover["value"] > 60
            ):
                dead_stock.append(
                    {
                        "sku_id": p.id,
                        "sku_code": p.sku_code,
                        "title": p.title,
                        "current_stock": p.current_stock,
                        "cover_days": cover["value"],
                    }
                )

        return {
            "seller_id": seller_id,
            "stockouts": stockouts,
            "low_cover": low_cover,
            "dead_stock": dead_stock,
            "data_status": "calculated",
        }
    finally:
        db.close()


# ── Tool: get_cancellation_breakdown ────────────────────────────────────

def get_cancellation_breakdown(seller_id: str, period_days: int = 30) -> dict[str, Any]:
    """Return cancellation metrics segmented by SKU for the period."""
    db = _get_db()
    try:
        today = date.today()
        start = today - timedelta(days=period_days - 1)
        rows = (
            db.query(DailyPerformance)
            .filter(
                DailyPerformance.seller_id == seller_id,
                DailyPerformance.perf_date >= start,
                DailyPerformance.perf_date <= today,
            )
            .all()
        )

        total_orders = sum(r.orders for r in rows)
        total_cancellations = sum(r.cancellations for r in rows)

        by_sku = {}
        for r in rows:
            if r.sku_id not in by_sku:
                by_sku[r.sku_id] = {"orders": 0, "cancellations": 0}
            by_sku[r.sku_id]["orders"] += r.orders
            by_sku[r.sku_id]["cancellations"] += r.cancellations

        sku_breakdown = []
        for sku_id, vals in by_sku.items():
            product = db.query(Product).filter(Product.id == sku_id).first()
            rate = (
                vals["cancellations"] / vals["orders"] if vals["orders"] > 0 else None
            )
            sku_breakdown.append(
                {
                    "sku_id": sku_id,
                    "sku_code": product.sku_code if product else None,
                    "title": product.title if product else None,
                    "orders": vals["orders"],
                    "cancellations": vals["cancellations"],
                    "cancellation_rate": rate,
                }
            )

        return {
            "seller_id": seller_id,
            "period_days": period_days,
            "total_orders": total_orders,
            "total_cancellations": total_cancellations,
            "cancellation_rate": (
                total_cancellations / total_orders if total_orders > 0 else None
            ),
            "by_sku": sku_breakdown,
            "data_status": "observed",
        }
    finally:
        db.close()


# ── Tool: get_festival_calendar ─────────────────────────────────────────

def get_festival_calendar(seller_id: str) -> dict[str, Any]:
    """Return upcoming Indian festival/regional events relevant to the seller."""
    db = _get_db()
    try:
        seller = _get_seller(db, seller_id)
        if not seller:
            raise ToolError(f"Seller {seller_id} not found")

        today = date.today()
        events = (
            db.query(CalendarEvent)
            .filter(CalendarEvent.end_date >= today)
            .order_by(CalendarEvent.start_date)
            .all()
        )

        # Filter by seller geography if specified
        relevant = []
        seller_state = seller.state
        for e in events:
            if e.geography and e.geography not in ("India", seller_state or ""):
                continue
            relevant.append(
                {
                    "event_name": e.event_name,
                    "event_type": e.event_type,
                    "start_date": e.start_date.isoformat(),
                    "end_date": e.end_date.isoformat(),
                    "geography": e.geography,
                    "shopping_lead_in_days": e.shopping_lead_in_days,
                    "category_relevance": e.category_relevance,
                    "confidence": e.confidence,  # verified / scenario / estimated
                    "source_url": e.source_url,
                    "data_status": "observed" if e.confidence == "verified" else "scenario",
                }
            )

        return {
            "seller_id": seller_id,
            "seller_state": seller_state,
            "upcoming_events": relevant,
            "data_status": "observed",
        }
    finally:
        db.close()


# ── Tool: calculate_replenishment_plan ──────────────────────────────────

def calculate_replenishment_plan(seller_id: str, sku_id: str) -> dict[str, Any]:
    """Calculate a replenishment recommendation for a single SKU.

    Formula: Reorder qty = forecast demand over lead time + safety stock
             - available stock - confirmed incoming stock
    Clamped at zero, then applied MOQ, budget, storage, margin constraints.
    """
    db = _get_db()
    try:
        product = (
            db.query(Product)
            .filter(Product.id == sku_id, Product.seller_id == seller_id)
            .first()
        )
        if not product:
            raise ToolError(f"SKU {sku_id} not found for seller {seller_id}")

        seller = _get_seller(db, seller_id)
        if not seller:
            raise ToolError(f"Seller {seller_id} not found")

        today = date.today()
        lead_time = product.supplier_lead_time_days

        # Forecast demand over lead time: use average daily units from last 30 days
        cover = calculate_stock_cover_days(db, seller_id, sku_id, today, days=30)
        avg_daily_units = None
        if cover["value"] is not None and cover["value"] > 0:
            avg_daily_units = product.current_stock / cover["value"]

        forecast_demand_lead_time = 0
        if avg_daily_units:
            forecast_demand_lead_time = round(avg_daily_units * lead_time)

        # Safety stock: simple heuristic based on lead time and demand volatility
        # (MVP: 1 day of average demand as safety stock)
        safety_stock = round(avg_daily_units) if avg_daily_units else 0

        available = product.current_stock
        incoming = product.incoming_stock

        reorder_qty = forecast_demand_lead_time + safety_stock - available - incoming
        reorder_qty = max(0, reorder_qty)

        # Apply MOQ
        if reorder_qty > 0 and reorder_qty < product.minimum_order_quantity:
            reorder_qty = product.minimum_order_quantity

        # Budget check
        estimated_cost = reorder_qty * product.unit_cost
        budget = seller.available_replenishment_budget
        within_budget = estimated_cost <= budget

        # Margin floor check
        margin_ok = True
        if product.minimum_margin is not None:
            # Estimate margin at current selling price
            margin = (product.selling_price - product.unit_cost) / product.selling_price
            margin_ok = margin >= product.minimum_margin

        # Storage check
        within_storage = True
        if seller.storage_capacity is not None:
            within_storage = (product.current_stock + reorder_qty) <= seller.storage_capacity

        return {
            "sku_id": sku_id,
            "sku_code": product.sku_code,
            "title": product.title,
            "current_stock": available,
            "incoming_stock": incoming,
            "supplier_lead_time_days": lead_time,
            "forecast_demand_lead_time": forecast_demand_lead_time,
            "safety_stock": safety_stock,
            "recommended_reorder_quantity": reorder_qty,
            "estimated_cost_paise": estimated_cost,
            "within_budget": within_budget,
            "budget_available_paise": budget,
            "margin_ok": margin_ok,
            "within_storage": within_storage,
            "minimum_order_quantity": product.minimum_order_quantity,
            "can_order": within_budget and margin_ok and within_storage and reorder_qty > 0,
            "data_status": "estimated",
            "assumptions": [
                "Demand forecast based on 30-day average daily units sold",
                "Safety stock = 1 day of average demand (MVP heuristic)",
                "Stockout-censored periods not separately modelled",
            ],
        }
    finally:
        db.close()


# ── Tool: create_recommendation ─────────────────────────────────────────

def create_recommendation(
    seller_id: str,
    title: str,
    problem_or_opportunity: str,
    suggested_action: str,
    evidence: Optional[str] = None,
    expected_impact: Optional[str] = None,
    cost_or_budget: Optional[int] = None,
    risk: str = "medium",
    confidence: str = "medium",
    urgency: str = "medium",
    priority: int = 0,
    assumptions: Optional[str] = None,
    what_to_measure_next: Optional[str] = None,
    requires_approval: bool = True,
    related_sku_ids: Optional[str] = None,
) -> dict[str, Any]:
    """Create a draft recommendation for seller approval."""
    db = _get_db()
    try:
        seller = _get_seller(db, seller_id)
        if not seller:
            raise ToolError(f"Seller {seller_id} not found")

        rec = Recommendation(
            seller_id=seller_id,
            title=title,
            problem_or_opportunity=problem_or_opportunity,
            evidence=evidence,
            suggested_action=suggested_action,
            expected_impact=expected_impact,
            cost_or_budget=cost_or_budget,
            risk=risk,
            confidence=confidence,
            urgency=urgency,
            priority=priority,
            assumptions=assumptions,
            what_to_measure_next=what_to_measure_next,
            requires_approval=requires_approval,
            related_sku_ids=related_sku_ids,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)

        return {
            "id": rec.id,
            "seller_id": rec.seller_id,
            "title": rec.title,
            "approval_status": rec.approval_status,
            "execution_status": rec.execution_status,
            "requires_approval": rec.requires_approval,
            "created_at": rec.created_at.isoformat(),
            "data_status": "calculated",
        }
    finally:
        db.close()


# ── Tool: get_recommendation_history ────────────────────────────────────

def get_recommendation_history(seller_id: str) -> dict[str, Any]:
    """Return all recommendations for a seller, most recent first."""
    db = _get_db()
    try:
        rows = (
            db.query(Recommendation)
            .filter(Recommendation.seller_id == seller_id)
            .order_by(Recommendation.created_at.desc())
            .all()
        )
        return {
            "seller_id": seller_id,
            "recommendations": [
                {
                    "id": r.id,
                    "title": r.title,
                    "problem_or_opportunity": r.problem_or_opportunity,
                    "suggested_action": r.suggested_action,
                    "expected_impact": r.expected_impact,
                    "risk": r.risk,
                    "confidence": r.confidence,
                    "urgency": r.urgency,
                    "priority": r.priority,
                    "approval_status": r.approval_status,
                    "execution_status": r.execution_status,
                    "requires_approval": r.requires_approval,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ],
            "data_status": "observed",
        }
    finally:
        db.close()


# ── Intelligence Tools (Phases 1–4) ────────────────────────────────────

def get_category_seasonality_breakdown(seller_id: str) -> dict[str, Any]:
    """Return category/segment distribution, seasonality tags, and supplier lead-time spread."""
    db = _get_db()
    try:
        products = (
            db.query(Product)
            .filter(Product.seller_id == seller_id, Product.active == True)  # noqa: E712
            .all()
        )
        categories: dict[str, dict[str, Any]] = {}
        fast_suppliers = 0
        long_lead_oos: list[dict[str, Any]] = []
        festival_sensitive: list[str] = []
        payday_sensitive: list[str] = []

        for p in products:
            cat = categories.setdefault(
                p.category,
                {"total_skus": 0, "oos_skus": 0, "staple_skus": 0, "discretionary_skus": 0},
            )
            cat["total_skus"] += 1
            if p.current_stock <= 0:
                cat["oos_skus"] += 1
            if getattr(p, "demand_segment", "discretionary") == "staple":
                cat["staple_skus"] += 1
            else:
                cat["discretionary_skus"] += 1
            if p.supplier_lead_time_days <= 4:
                fast_suppliers += 1
            if p.current_stock <= 0 and p.supplier_lead_time_days >= 9:
                long_lead_oos.append({
                    "sku_code": p.sku_code,
                    "title": p.title,
                    "lead_time_days": p.supplier_lead_time_days,
                    "seasonality_tag": getattr(p, "seasonality_tag", "evergreen"),
                })
            if getattr(p, "is_festival_sensitive", False):
                festival_sensitive.append(p.title)
            if getattr(p, "is_payday_sensitive", False):
                payday_sensitive.append(p.title)

        return {
            "seller_id": seller_id,
            "by_category": categories,
            "fast_lead_sku_count": fast_suppliers,
            "long_lead_stockout_skus": long_lead_oos[:6],
            "festival_sensitive_sample": festival_sensitive[:6],
            "payday_sensitive_sample": payday_sensitive[:6],
            "data_status": "observed",
        }
    finally:
        db.close()


def calculate_stockout_impact_tool(seller_id: str, period_days: int = 30) -> dict[str, Any]:
    """Quantify lost units and lost revenue caused by stockouts."""
    db = _get_db()
    try:
        return _calculate_stockout_impact(db, seller_id, period_days=period_days)
    finally:
        db.close()


def decompose_revenue_change_tool(seller_id: str, period_days: int = 30) -> dict[str, Any]:
    """Break revenue change into Volume, Price, Availability/Stockout, Cancellation, and Mix effects."""
    db = _get_db()
    try:
        return _decompose_revenue_change(db, seller_id, period_days=period_days)
    finally:
        db.close()


def simulate_what_if_tool(
    seller_id: str,
    budget_inr: float = 15000.0,
    sku_id: Optional[str] = None,
    delay_days: int = 7,
    festival_uplift_pct: float = 25.0,
) -> dict[str, Any]:
    """Simulate a What-If restocking budget vs delaying replenishment."""
    db = _get_db()
    try:
        return _simulate_what_if_scenario(
            db,
            seller_id,
            budget_inr=budget_inr,
            sku_id=sku_id,
            delay_days=delay_days,
            festival_uplift_pct=festival_uplift_pct,
        )
    finally:
        db.close()


def get_smart_replenishment_plan_tool(
    seller_id: str, auto_create_recommendation: bool = False
) -> dict[str, Any]:
    """Build profile-aligned, lead-time-aware batch replenishment plan."""
    db = _get_db()
    try:
        return _build_smart_replenishment_plan(
            db, seller_id, auto_create_recommendation=auto_create_recommendation
        )
    finally:
        db.close()


def get_proactive_alerts_tool(seller_id: str) -> dict[str, Any]:
    """Return prioritized proactive KAM risk alerts across stockouts, cancellations, and festivals."""
    db = _get_db()
    try:
        alerts = _generate_proactive_alerts(db, seller_id, channel="voice", persist=True)
        return {"seller_id": seller_id, "alerts": alerts[:5], "data_status": "calculated"}
    finally:
        db.close()


def get_outcome_track_record_tool(seller_id: str) -> dict[str, Any]:
    """Return historical recommendation outcome track record to weight confidence."""
    db = _get_db()
    try:
        return _get_outcome_track_record(db, seller_id)
    finally:
        db.close()


def search_catalog_skus(
    seller_id: str,
    query: str = "",
    limit: int = 20,
) -> dict[str, Any]:
    """Search seller's active SKU catalog by product title, code, category, or seasonality."""
    db = _get_db()
    try:
        products = (
            db.query(Product)
            .filter(Product.seller_id == seller_id, Product.active == True)  # noqa: E712
            .order_by(Product.current_stock.asc(), Product.title.asc())
            .all()
        )
        q = (query or "").strip().lower()
        tokens = [t for t in q.split() if len(t) >= 2]
        matches = []
        for p in products:
            haystack = " ".join([
                p.id or "",
                p.sku_code or "",
                p.title or "",
                p.category or "",
                p.subcategory or "",
                getattr(p, "seasonality_tag", "") or "",
                getattr(p, "demand_segment", "") or "",
            ]).lower()
            if not tokens or all(tok in haystack for tok in tokens) or any(tok in haystack for tok in tokens):
                score = sum(1 for tok in tokens if tok in (p.title or "").lower()) if tokens else 0
                price_inr = round((p.selling_price or 0) / 100.0, 2)
                cost_inr = round((p.unit_cost or 0) / 100.0, 2)
                margin_pct = (
                    round(((p.selling_price - p.unit_cost) / p.selling_price) * 100.0, 1)
                    if p.selling_price
                    else None
                )
                matches.append((score, {
                    "sku_id": p.id,
                    "sku_code": p.sku_code,
                    "title": p.title,
                    "category": p.category,
                    "subcategory": p.subcategory,
                    "demand_segment": getattr(p, "demand_segment", "discretionary"),
                    "seasonality_tag": getattr(p, "seasonality_tag", "evergreen"),
                    "selling_price_inr": price_inr,
                    "unit_cost_inr": cost_inr,
                    "margin_pct": margin_pct,
                    "current_stock": p.current_stock,
                    "incoming_stock": p.incoming_stock,
                    "supplier_lead_time_days": p.supplier_lead_time_days,
                    "status": "out_of_stock" if p.current_stock <= 0 else "in_stock",
                }))

        matches.sort(key=lambda item: (-item[0], item[1]["current_stock"]))
        capped = [item[1] for item in matches[: max(1, min(limit, 30))]]
        return {
            "seller_id": seller_id,
            "query": query,
            "matched_count": len(capped),
            "products": capped,
            "data_status": "observed",
        }
    finally:
        db.close()


# ── Tool registry ───────────────────────────────────────────────────────

TOOL_REGISTRY = {
    "get_seller_profile": get_seller_profile,
    "get_dashboard_kpis": get_dashboard_kpis,
    "get_sales_trend": get_sales_trend,
    "get_sku_performance": get_sku_performance,
    "get_inventory_health": get_inventory_health,
    "get_cancellation_breakdown": get_cancellation_breakdown,
    "get_festival_calendar": get_festival_calendar,
    "calculate_replenishment_plan": calculate_replenishment_plan,
    "create_recommendation": create_recommendation,
    "get_recommendation_history": get_recommendation_history,
    "get_category_seasonality_breakdown": get_category_seasonality_breakdown,
    "calculate_stockout_impact": calculate_stockout_impact_tool,
    "decompose_revenue_change": decompose_revenue_change_tool,
    "simulate_what_if_scenario": simulate_what_if_tool,
    "get_smart_replenishment_plan": get_smart_replenishment_plan_tool,
    "get_proactive_alerts": get_proactive_alerts_tool,
    "get_outcome_track_record": get_outcome_track_record_tool,
    "search_catalog_skus": search_catalog_skus,
}

TOOL_DESCRIPTIONS = {
    "get_seller_profile": "Get the seller's profile, business goals, budget, risk tolerance, and constraints.",
    "get_dashboard_kpis": "Get current-period KPIs: revenue, orders, units, ASP, cancellation, return, conversion, stockouts, inventory value, and period-over-period change.",
    "get_sales_trend": "Get daily net sales trend for the period.",
    "get_sku_performance": "Get a single SKU's current stock, cover days, recent sales, and stockout status.",
    "get_inventory_health": "Get inventory health: stockouts, low cover days, and dead stock candidates.",
    "get_cancellation_breakdown": "Get cancellation metrics segmented by SKU for the period.",
    "get_festival_calendar": "Get upcoming Indian festival and regional events relevant to the seller.",
    "calculate_replenishment_plan": "Calculate a replenishment recommendation for a SKU (reorder qty, cost, budget/margin/storage checks).",
    "create_recommendation": "Create a draft recommendation requiring seller approval before execution.",
    "get_recommendation_history": "Get the seller's past recommendations with approval/execution status.",
    "get_category_seasonality_breakdown": "Get category, staple/discretionary mix, seasonality tags, and supplier lead-time breakdown.",
    "calculate_stockout_impact": "Quantify lost units and lost revenue from stockout-censored demand.",
    "decompose_revenue_change": "Decompose revenue change into Volume, Price, Availability/Stockout, Cancellation, and Mix components.",
    "simulate_what_if_scenario": "Simulate a What-If restocking budget spend vs delay opportunity cost.",
    "get_smart_replenishment_plan": "Generate a prioritized, profile-aware batch PO replenishment plan.",
    "get_proactive_alerts": "Fetch proactive KAM alerts for imminent stockouts, 3-day cancellation spikes, and festival readiness.",
    "get_outcome_track_record": "Retrieve historical recommendation outcomes to weight confidence by proven ROI.",
    "search_catalog_skus": "Search seller's product catalog by keyword (product title, SKU code, category, seasonality) to inspect prices, margins, stock levels, and SKU IDs.",
}
