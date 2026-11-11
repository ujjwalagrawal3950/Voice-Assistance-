"""Deterministic KPI calculations.

Every function is independently testable and returns a result carrying:
- the computed value
- the formula/definition used
- the period and comparison period
- source fields
- missing-data behaviour
- unit and currency
- calculation timestamp

The LLM must not calculate these from raw rows.
"""

from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DailyPerformance, Product


def _paise_to_inr(paise: int) -> str:
    """Format paise as INR string."""
    inr = Decimal(paise) / Decimal(100)
    return f"₹{inr:,.2f}"


def _safe_divide(numerator: int, denominator: int) -> Optional[float]:
    """Return None when denominator is zero (missing data, not zero)."""
    if denominator == 0:
        return None
    return numerator / denominator


def _period_bounds(period_end: date, days: int) -> tuple[date, date]:
    start = period_end - timedelta(days=days - 1)
    return start, period_end


def _query_period_sales(
    db: Session, seller_id: str, sku_ids: Optional[List[str]], start: date, end: date
) -> List[DailyPerformance]:
    stmt = select(DailyPerformance).where(
        DailyPerformance.seller_id == seller_id,
        DailyPerformance.perf_date >= start,
        DailyPerformance.perf_date <= end,
    )
    if sku_ids:
        stmt = stmt.where(DailyPerformance.sku_id.in_(sku_ids))
    return db.execute(stmt).scalars().all()


def calculate_gross_sales(
    db: Session,
    seller_id: str,
    period_end: date,
    days: int = 30,
    sku_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Gross sales = sum of gross_sales over the period.

    Treatment of discounts: gross_sales is recorded before discounts.
    Net sales = gross_sales - discounts - cancellations - returns.
    """
    start, end = _period_bounds(period_end, days)
    rows = _query_period_sales(db, seller_id, sku_ids, start, end)
    total = sum(r.gross_sales for r in rows)
    return {
        "value": total,
        "unit": "paise",
        "currency": "INR",
        "formula": "SUM(gross_sales) over period",
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "source_fields": ["daily_performance.gross_sales"],
        "missing_data_behaviour": "rows with no performance record contribute 0",
        "calculated_at": datetime.utcnow().isoformat(),
        "data_status": "calculated",
    }


def calculate_net_sales(
    db: Session,
    seller_id: str,
    period_end: date,
    days: int = 30,
    sku_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Net sales = SUM(net_sales) where net_sales = gross_sales - discounts - cancellations - returns."""
    start, end = _period_bounds(period_end, days)
    rows = _query_period_sales(db, seller_id, sku_ids, start, end)
    total = sum(r.net_sales for r in rows)
    return {
        "value": total,
        "unit": "paise",
        "currency": "INR",
        "formula": "SUM(net_sales) over period",
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "source_fields": ["daily_performance.net_sales"],
        "missing_data_behaviour": "rows with no performance record contribute 0",
        "calculated_at": datetime.utcnow().isoformat(),
        "data_status": "calculated",
    }


def calculate_orders(
    db: Session,
    seller_id: str,
    period_end: date,
    days: int = 30,
    sku_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    start, end = _period_bounds(period_end, days)
    rows = _query_period_sales(db, seller_id, sku_ids, start, end)
    total = sum(r.orders for r in rows)
    return {
        "value": total,
        "unit": "count",
        "currency": None,
        "formula": "SUM(orders) over period",
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "source_fields": ["daily_performance.orders"],
        "missing_data_behaviour": "rows with no performance record contribute 0",
        "calculated_at": datetime.utcnow().isoformat(),
        "data_status": "calculated",
    }


def calculate_units_sold(
    db: Session,
    seller_id: str,
    period_end: date,
    days: int = 30,
    sku_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    start, end = _period_bounds(period_end, days)
    rows = _query_period_sales(db, seller_id, sku_ids, start, end)
    total = sum(r.units_sold for r in rows)
    return {
        "value": total,
        "unit": "count",
        "currency": None,
        "formula": "SUM(units_sold) over period",
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "source_fields": ["daily_performance.units_sold"],
        "missing_data_behaviour": "rows with no performance record contribute 0",
        "calculated_at": datetime.utcnow().isoformat(),
        "data_status": "calculated",
    }


def calculate_average_selling_price(
    db: Session,
    seller_id: str,
    period_end: date,
    days: int = 30,
    sku_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """ASP = net_sales / orders. Denominator is orders (not units)."""
    start, end = _period_bounds(period_end, days)
    rows = _query_period_sales(db, seller_id, sku_ids, start, end)
    total_net = sum(r.net_sales for r in rows)
    total_orders = sum(r.orders for r in rows)
    asp_paise = None
    asp_inr = None
    if total_orders > 0:
        asp_paise = int(round(total_net / total_orders))
        asp_inr = _paise_to_inr(asp_paise)
    return {
        "value": asp_paise,
        "unit": "paise",
        "currency": "INR",
        "formula": "SUM(net_sales) / SUM(orders)",
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "source_fields": ["daily_performance.net_sales", "daily_performance.orders"],
        "missing_data_behaviour": "None when orders == 0",
        "calculated_at": datetime.utcnow().isoformat(),
        "data_status": "calculated",
    }


def calculate_cancellation_rate(
    db: Session,
    seller_id: str,
    period_end: date,
    days: int = 30,
    sku_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Cancellation rate = SUM(cancellations) / SUM(orders)."""
    start, end = _period_bounds(period_end, days)
    rows = _query_period_sales(db, seller_id, sku_ids, start, end)
    total_cancellations = sum(r.cancellations for r in rows)
    total_orders = sum(r.orders for r in rows)
    rate = _safe_divide(total_cancellations, total_orders)
    return {
        "value": rate,
        "unit": "fraction",
        "currency": None,
        "formula": "SUM(cancellations) / SUM(orders)",
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "source_fields": ["daily_performance.cancellations", "daily_performance.orders"],
        "missing_data_behaviour": "None when orders == 0",
        "calculated_at": datetime.utcnow().isoformat(),
        "data_status": "calculated",
    }


def calculate_return_rate(
    db: Session,
    seller_id: str,
    period_end: date,
    days: int = 30,
    sku_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Return rate = SUM(returns) / SUM(orders)."""
    start, end = _period_bounds(period_end, days)
    rows = _query_period_sales(db, seller_id, sku_ids, start, end)
    total_returns = sum(r.returns for r in rows)
    total_orders = sum(r.orders for r in rows)
    rate = _safe_divide(total_returns, total_orders)
    return {
        "value": rate,
        "unit": "fraction",
        "currency": None,
        "formula": "SUM(returns) / SUM(orders)",
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "source_fields": ["daily_performance.returns", "daily_performance.orders"],
        "missing_data_behaviour": "None when orders == 0",
        "calculated_at": datetime.utcnow().isoformat(),
        "data_status": "calculated",
    }


def calculate_conversion_rate(
    db: Session,
    seller_id: str,
    period_end: date,
    days: int = 30,
    sku_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Conversion rate = SUM(orders) / SUM(views) when views exist; else None."""
    start, end = _period_bounds(period_end, days)
    rows = _query_period_sales(db, seller_id, sku_ids, start, end)
    total_orders = sum(r.orders for r in rows)
    total_views = sum(r.views or 0 for r in rows)
    rate = _safe_divide(total_orders, total_views)
    return {
        "value": rate,
        "unit": "fraction",
        "currency": None,
        "formula": "SUM(orders) / SUM(views)",
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "source_fields": ["daily_performance.orders", "daily_performance.views"],
        "missing_data_behaviour": "None when views == 0 or views missing",
        "calculated_at": datetime.utcnow().isoformat(),
        "data_status": "calculated",
    }


def calculate_stockout_sku_count(
    db: Session,
    seller_id: str,
    as_of: Optional[date] = None,
) -> Dict[str, Any]:
    """Count of SKUs with current_stock == 0 (using latest product snapshot)."""
    if as_of is None:
        as_of = date.today()
    from app.models import Product

    rows = (
        db.query(Product)
        .filter(Product.seller_id == seller_id, Product.active == True)  # noqa: E712
        .all()
    )
    stockout_count = sum(1 for p in rows if p.current_stock <= 0)
    return {
        "value": stockout_count,
        "unit": "count",
        "currency": None,
        "formula": "COUNT(products WHERE current_stock <= 0 AND active = true)",
        "period_start": None,
        "period_end": as_of.isoformat(),
        "source_fields": ["products.current_stock", "products.active"],
        "missing_data_behaviour": "inactive SKUs excluded",
        "calculated_at": datetime.utcnow().isoformat(),
        "data_status": "observed",
    }


def calculate_inventory_value(
    db: Session,
    seller_id: str,
) -> Dict[str, Any]:
    """Inventory value at cost and at selling price (labelled clearly)."""
    from app.models import Product

    rows = db.query(Product).filter(Product.seller_id == seller_id, Product.active == True).all()  # noqa: E712
    value_at_cost = sum(p.unit_cost * p.current_stock for p in rows)
    value_at_selling = sum(p.selling_price * p.current_stock for p in rows)
    return {
        "value_at_cost": value_at_cost,
        "value_at_selling": value_at_selling,
        "unit": "paise",
        "currency": "INR",
        "formula_cost": "SUM(unit_cost * current_stock)",
        "formula_selling": "SUM(selling_price * current_stock)",
        "source_fields": ["products.unit_cost", "products.selling_price", "products.current_stock"],
        "calculated_at": datetime.utcnow().isoformat(),
        "data_status": "calculated",
    }


def calculate_stock_cover_days(
    db: Session,
    seller_id: str,
    sku_id: str,
    period_end: date,
    days: int = 30,
) -> Dict[str, Any]:
    """Days of stock cover = current_stock / average daily units sold over period."""
    from app.models import Product

    product = db.query(Product).filter(Product.id == sku_id, Product.seller_id == seller_id).first()
    if not product:
        return {
            "value": None,
            "unit": "days",
            "currency": None,
            "formula": "current_stock / average_daily_units_sold",
            "period_start": None,
            "period_end": None,
            "source_fields": ["products.current_stock", "daily_performance.units_sold"],
            "missing_data_behaviour": "None when product not found",
            "calculated_at": datetime.utcnow().isoformat(),
            "data_status": "calculated",
        }

    start, end = _period_bounds(period_end, days)
    rows = _query_period_sales(db, seller_id, [sku_id], start, end)
    total_units = sum(r.units_sold for r in rows)
    avg_daily = total_units / days if days > 0 else 0
    cover_days = None
    if avg_daily > 0:
        cover_days = round(product.current_stock / avg_daily, 1)
    return {
        "value": cover_days,
        "unit": "days",
        "currency": None,
        "formula": "current_stock / (SUM(units_sold) / period_days)",
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "source_fields": ["products.current_stock", "daily_performance.units_sold"],
        "missing_data_behaviour": "None when average daily units == 0",
        "calculated_at": datetime.utcnow().isoformat(),
        "data_status": "calculated",
    }


def period_over_period_change(
    current: float,
    previous: float,
) -> Optional[float]:
    """Absolute and percentage change between two periods.

    Returns None when previous is zero or None (avoid division by zero).
    """
    if previous is None or previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 2)
