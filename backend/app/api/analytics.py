"""Cancellation breakdown API endpoint."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.api.deps import get_current_seller_id, get_db_session
from app.schemas import WhatIfRequest
from app.services.intelligence import (
    calculate_stockout_impact,
    decompose_revenue_change,
    simulate_what_if_scenario,
)
from app.services.kpi import calculate_cancellation_rate
from app.models import DailyPerformance

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/cancellations")
def get_cancellation_breakdown(
    period_days: int = Query(default=30, ge=1, le=365),
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    """Return cancellation metrics segmented by SKU for the period."""
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
        product = db.query(__import__("app.models", fromlist=["Product"]).Product).filter(
            __import__("app.models", fromlist=["Product"]).Product.id == sku_id
        ).first()
        rate = vals["cancellations"] / vals["orders"] if vals["orders"] > 0 else None
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


@router.get("/stockout-impact")
def get_stockout_impact(
    period_days: int = Query(default=30, ge=1, le=365),
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    """Quantify lost units & lost revenue caused by stockouts."""
    return calculate_stockout_impact(db, seller_id, period_days=period_days)


@router.get("/decomposition")
def get_revenue_decomposition(
    period_days: int = Query(default=30, ge=1, le=365),
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    """Break period-over-period revenue change into Volume, Price, Availability, and Cancellation effects."""
    return decompose_revenue_change(db, seller_id, period_days=period_days)


@router.post("/what-if")
def run_what_if_simulation(
    payload: WhatIfRequest,
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    """Run a deterministic What-If replenishment & delay scenario aligned to the seller's profile."""
    return simulate_what_if_scenario(
        db,
        seller_id,
        budget_inr=payload.budget_inr,
        sku_id=payload.sku_id,
        delay_days=payload.delay_days,
        festival_uplift_pct=payload.festival_uplift_pct,
    )
