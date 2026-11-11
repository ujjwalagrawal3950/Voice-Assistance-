"""Demand forecasting service.

Implements transparent baselines per docs/06:
- Recent moving average
- Same-weekday seasonal naive where enough history exists
- Prior-year comparable period only when data is available and comparable

All forecasts carry provenance: model name/version, training data window,
latest data date, key drivers, stockout/data-quality caveats, backtest metrics,
and whether festival uplift is learned / rule-based / scenario-only.
"""

from datetime import date, timedelta
from typing import Any, Optional

import numpy as np

from app.database import SessionLocal
from app.models import CalendarEvent, DailyPerformance, Product


def _get_db():
    return SessionLocal()


def _safe_divide(numerator: float, denominator: float) -> Optional[float]:
    if denominator == 0 or denominator is None:
        return None
    return numerator / denominator


def _get_sku_history(
    db, seller_id: str, sku_id: str, end_date: date, days: int
) -> list[tuple[date, int]]:
    """Return list of (date, units_sold) for a SKU over the lookback window."""
    start = end_date - timedelta(days=days - 1)
    rows = (
        db.query(DailyPerformance)
        .filter(
            DailyPerformance.seller_id == seller_id,
            DailyPerformance.sku_id == sku_id,
            DailyPerformance.perf_date >= start,
            DailyPerformance.perf_date <= end_date,
        )
        .order_by(DailyPerformance.perf_date)
        .all()
    )
    return [(r.perf_date, r.units_sold) for r in rows]


def moving_average_forecast(
    db, seller_id: str, sku_id: str, horizon_days: int = 7, lookback_days: int = 30
) -> dict[str, Any]:
    """Forecast using a simple moving average of recent daily units sold.

    Does not use future information. Stockout periods are flagged as caveats
    because demand is censored when stock was unavailable.
    """
    end_date = date.today()
    history = _get_sku_history(db, seller_id, sku_id, end_date, lookback_days)

    if not history:
        return {
            "sku_id": sku_id,
            "horizon_days": horizon_days,
            "forecast": [],
            "model": "moving_average",
            "model_version": "1.0",
            "error": "No history available",
            "data_status": "estimated",
        }

    units = [u for _, u in history]
    avg_daily = sum(units) / len(units) if units else 0

    # Count stockout days in the lookback window
    stockout_days = sum(
        1
        for _, u in history
        if u == 0
    )

    forecast = []
    for i in range(horizon_days):
        forecast_date = end_date + timedelta(days=i + 1)
        forecast.append(
            {
                "date": forecast_date.isoformat(),
                "forecast_units": round(avg_daily, 1),
                "lower_bound": round(max(0, avg_daily * 0.7), 1),
                "upper_bound": round(avg_daily * 1.3, 1),
            }
        )

    return {
        "sku_id": sku_id,
        "horizon_days": horizon_days,
        "lookback_days": lookback_days,
        "forecast": forecast,
        "model": "moving_average",
        "model_version": "1.0",
        "training_window_start": (end_date - timedelta(days=lookback_days - 1)).isoformat(),
        "training_window_end": end_date.isoformat(),
        "latest_data_date": end_date.isoformat(),
        "avg_daily_units": round(avg_daily, 1),
        "stockout_days_in_history": stockout_days,
        "data_quality_caveats": [
            "Stockout-censored periods: days with 0 units may reflect stock unavailability, not zero demand",
            "Simple moving average does not capture trend or seasonality",
            "Festival uplift is scenario-only (not learned)",
        ],
        "festival_uplift_type": "scenario-only",
        "data_status": "estimated",
    }


def seasonal_naive_forecast(
    db, seller_id: str, sku_id: str, horizon_days: int = 7, lookback_days: int = 84
) -> dict[str, Any]:
    """Forecast using same-weekday seasonal naive.

    For each forecast day, uses the average of units sold on the same weekday
    from previous weeks in the lookback window. Requires at least 2 weeks of
    history to be meaningful.
    """
    end_date = date.today()
    history = _get_sku_history(db, seller_id, sku_id, end_date, lookback_days)

    if len(history) < 14:
        return {
            "sku_id": sku_id,
            "horizon_days": horizon_days,
            "forecast": [],
            "model": "seasonal_naive",
            "model_version": "1.0",
            "error": "Insufficient history (need at least 14 days)",
            "data_status": "estimated",
        }

    # Group units by weekday (0=Monday ... 6=Sunday)
    weekday_units: dict[int, list[int]] = {i: [] for i in range(7)}
    for d, u in history:
        weekday_units[d.weekday()].append(u)

    weekday_avg = {
        wd: (sum(u) / len(u) if u else 0) for wd, u in weekday_units.items()
    }

    forecast = []
    for i in range(horizon_days):
        forecast_date = end_date + timedelta(days=i + 1)
        wd = forecast_date.weekday()
        forecast.append(
            {
                "date": forecast_date.isoformat(),
                "forecast_units": round(weekday_avg[wd], 1),
                "lower_bound": round(max(0, weekday_avg[wd] * 0.6), 1),
                "upper_bound": round(weekday_avg[wd] * 1.4, 1),
            }
        )

    return {
        "sku_id": sku_id,
        "horizon_days": horizon_days,
        "lookback_days": lookback_days,
        "forecast": forecast,
        "model": "seasonal_naive",
        "model_version": "1.0",
        "training_window_start": (end_date - timedelta(days=lookback_days - 1)).isoformat(),
        "training_window_end": end_date.isoformat(),
        "latest_data_date": end_date.isoformat(),
        "weekday_averages": {str(k): round(v, 1) for k, v in weekday_avg.items()},
        "data_quality_caveats": [
            "Seasonal naive assumes demand repeats by weekday only",
            "Stockout-censored periods may bias weekday averages downward",
            "Festival uplift is scenario-only (not learned)",
        ],
        "festival_uplift_type": "scenario-only",
        "data_status": "estimated",
    }


def backtest_forecast(
    db, seller_id: str, sku_id: str, method: str = "moving_average"
) -> dict[str, Any]:
    """Simple chronological backtest: train on first 70%, test on last 30%.

    Reports MAE and WAPE. Excludes stockout-censored days from test set.
    """
    end_date = date.today()
    history = _get_sku_history(db, seller_id, sku_id, end_date, days=180)

    if len(history) < 30:
        return {
            "sku_id": sku_id,
            "method": method,
            "error": "Insufficient history for backtest",
            "mae": None,
            "wape": None,
        }

    split_idx = int(len(history) * 0.7)
    train = history[:split_idx]
    test = history[split_idx:]

    # Exclude stockout days from test (censored demand)
    test_valid = [(d, u) for d, u in test if u > 0]
    if not test_valid:
        return {
            "sku_id": sku_id,
            "method": method,
            "error": "No non-stockout test days",
            "mae": None,
            "wape": None,
        }

    if method == "moving_average":
        train_units = [u for _, u in train]
        avg = sum(train_units) / len(train_units) if train_units else 0
        predictions = [avg] * len(test_valid)
    else:  # seasonal_naive
        weekday_units: dict[int, list[int]] = {i: [] for i in range(7)}
        for d, u in train:
            weekday_units[d.weekday()].append(u)
        weekday_avg = {
            wd: (sum(u) / len(u) if u else 0) for wd, u in weekday_units.items()
        }
        predictions = [weekday_avg[d.weekday()] for d, _ in test_valid]

    actuals = [u for _, u in test_valid]
    mae = sum(abs(p - a) for p, a in zip(predictions, actuals)) / len(actuals)
    total_actual = sum(actuals)
    wape = (sum(abs(p - a) for p, a in zip(predictions, actuals)) / total_actual) if total_actual > 0 else None

    return {
        "sku_id": sku_id,
        "method": method,
        "train_days": len(train),
        "test_days": len(test_valid),
        "mae": round(mae, 2),
        "wape": round(wape, 2) if wape is not None else None,
        "data_status": "estimated",
    }


def get_forecast(
    db, seller_id: str, sku_id: str, horizon_days: int = 7
) -> dict[str, Any]:
    """Get the best available forecast for a SKU.

    Prefers seasonal_naive when enough history exists, otherwise moving_average.
    Includes backtest metrics for transparency.
    """
    # Check history length
    end_date = date.today()
    history = _get_sku_history(db, seller_id, sku_id, end_date, days=84)

    if len(history) >= 14:
        result = seasonal_naive_forecast(db, seller_id, sku_id, horizon_days)
    else:
        result = moving_average_forecast(db, seller_id, sku_id, horizon_days)

    # Add backtest metrics
    backtest = backtest_forecast(db, seller_id, sku_id, result["model"])
    result["backtest"] = backtest

    # Add festival context for the forecast horizon
    horizon_end = end_date + timedelta(days=horizon_days)
    festivals = (
        db.query(CalendarEvent)
        .filter(
            CalendarEvent.start_date <= horizon_end,
            CalendarEvent.end_date >= end_date,
        )
        .all()
    )
    if festivals:
        result["upcoming_festivals"] = [
            {
                "event_name": f.event_name,
                "event_type": f.event_type,
                "start_date": f.start_date.isoformat(),
                "end_date": f.end_date.isoformat(),
                "confidence": f.confidence,
                "data_status": "observed" if f.confidence == "verified" else "scenario",
            }
            for f in festivals
        ]
        result["data_quality_caveats"].append(
            "Festival uplift is scenario-only; no learned demand model has been trained"
        )

    return result


def calculate_replenishment_recommendation(
    db, seller_id: str, sku_id: str
) -> dict[str, Any]:
    """Calculate a replenishment recommendation for a SKU.

    Formula: Reorder qty = forecast demand over lead time + safety stock
             - available stock - confirmed incoming stock
    Clamped at zero, then applied MOQ, budget, storage, margin constraints.
    """
    from app.models import Product, Seller

    product = (
        db.query(Product)
        .filter(Product.id == sku_id, Product.seller_id == seller_id)
        .first()
    )
    if not product:
        return {"error": f"SKU {sku_id} not found"}

    seller = db.query(Seller).filter(Seller.id == seller_id).first()
    if not seller:
        return {"error": f"Seller {seller_id} not found"}

    today = date.today()
    lead_time = product.supplier_lead_time_days

    # Get forecast over lead time
    forecast = get_forecast(db, seller_id, sku_id, horizon_days=lead_time + 7)
    forecast_units = sum(f["forecast_units"] for f in forecast.get("forecast", []))
    # Demand over lead time only (first lead_time days)
    lead_time_forecast = sum(
        f["forecast_units"] for f in forecast.get("forecast", [])[:lead_time]
    )

    # Safety stock: 1 day of average demand (MVP heuristic)
    avg_daily = forecast_units / max(1, len(forecast.get("forecast", [])))
    safety_stock = round(avg_daily)

    available = product.current_stock
    incoming = product.incoming_stock

    reorder_qty = lead_time_forecast + safety_stock - available - incoming
    reorder_qty = max(0, reorder_qty)

    # Apply MOQ
    moq = product.minimum_order_quantity
    if reorder_qty > 0 and reorder_qty < moq:
        reorder_qty = moq

    # Budget check
    estimated_cost = reorder_qty * product.unit_cost
    budget = seller.available_replenishment_budget
    within_budget = estimated_cost <= budget

    # Margin floor check
    margin_ok = True
    if product.minimum_margin is not None and product.selling_price > 0:
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
        "forecast_demand_lead_time": round(lead_time_forecast, 1),
        "safety_stock": safety_stock,
        "recommended_reorder_quantity": reorder_qty,
        "estimated_cost_paise": estimated_cost,
        "estimated_cost_inr": round(estimated_cost / 100, 2),
        "within_budget": within_budget,
        "budget_available_paise": budget,
        "margin_ok": margin_ok,
        "within_storage": within_storage,
        "minimum_order_quantity": moq,
        "can_order": within_budget and margin_ok and within_storage and reorder_qty > 0,
        "data_status": "estimated",
        "assumptions": [
            "Demand forecast based on seasonal-naive / moving-average baseline",
            "Safety stock = 1 day of average demand (MVP heuristic)",
            "Festival uplift is scenario-only, not learned",
            "Stockout-censored periods not separately modelled",
        ],
    }
