"""Dashboard summary endpoint using deterministic KPI calculations."""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_seller_id, get_db_session
from app.models import Product
from app.services.intelligence import generate_proactive_alerts
from app.services.kpi import (
    calculate_gross_sales,
    calculate_net_sales,
    calculate_orders,
    calculate_units_sold,
    calculate_average_selling_price,
    calculate_cancellation_rate,
    calculate_return_rate,
    calculate_conversion_rate,
    calculate_stockout_sku_count,
    calculate_inventory_value,
    calculate_stock_cover_days,
    period_over_period_change,
)
from app.schemas import DashboardSummary

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    period_days: int = Query(default=30, ge=1, le=365),
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    today = date.today()
    period_end = today
    period_start = period_end - timedelta(days=period_days - 1)
    comparison_end = period_start - timedelta(days=1)
    comparison_start = comparison_end - timedelta(days=period_days - 1)

    # Current period KPIs
    revenue = calculate_gross_sales(db, seller_id, period_end, period_days)
    net_revenue = calculate_net_sales(db, seller_id, period_end, period_days)
    orders = calculate_orders(db, seller_id, period_end, period_days)
    units = calculate_units_sold(db, seller_id, period_end, period_days)
    asp = calculate_average_selling_price(db, seller_id, period_end, period_days)
    cancellation = calculate_cancellation_rate(db, seller_id, period_end, period_days)
    returns = calculate_return_rate(db, seller_id, period_end, period_days)
    conversion = calculate_conversion_rate(db, seller_id, period_end, period_days)
    stockouts = calculate_stockout_sku_count(db, seller_id, as_of=period_end)
    inventory = calculate_inventory_value(db, seller_id)

    # Comparison period KPIs (for period-over-period change)
    prev_revenue = calculate_gross_sales(db, seller_id, comparison_end, period_days)
    prev_orders = calculate_orders(db, seller_id, comparison_end, period_days)

    revenue_change = period_over_period_change(
        revenue["value"], prev_revenue["value"]
    )
    orders_change = period_over_period_change(
        orders["value"], prev_orders["value"]
    )

    # Top alerts (rule-based + SKU-level proactive intelligence)
    proactive = generate_proactive_alerts(db, seller_id, persist=False)
    alerts = [a["title"] for a in proactive[:3]]
    if not alerts:
        if stockouts["value"] > 0:
            alerts.append(f"{stockouts['value']} product(s) currently out of stock")
        if cancellation["value"] is not None and cancellation["value"] > 0.10:
            alerts.append(f"Cancellation rate at {cancellation['value']*100:.0f}% — above 10% threshold")
        if revenue_change is not None and revenue_change < -10:
            alerts.append(f"Revenue down {abs(revenue_change)}% vs previous period")

    # Stock cover for the seller overall (simple average across SKUs)
    products = db.query(Product).filter(Product.seller_id == seller_id, Product.active == True).all()  # noqa: E712
    cover_values = []
    for p in products:
        cover = calculate_stock_cover_days(db, seller_id, p.id, period_end, period_days)
        if cover["value"] is not None:
            cover_values.append(cover["value"])
    avg_cover = round(sum(cover_values) / len(cover_values), 1) if cover_values else None

    return {
        "seller_id": seller_id,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "comparison_start": comparison_start.isoformat(),
        "comparison_end": comparison_end.isoformat(),
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
        "days_of_stock_cover": avg_cover,
        "revenue_change_pct": revenue_change,
        "orders_change_pct": orders_change,
        "top_alerts": alerts,
        "data_status": "calculated",
        "calculated_at": revenue["calculated_at"],
    }
