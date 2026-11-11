"""Forecast and replenishment API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_seller_id, get_db_session
from app.services.forecasting import (
    get_forecast,
    calculate_replenishment_recommendation,
)
from app.services.intelligence import build_smart_replenishment_plan

router = APIRouter(prefix="/api/forecasts", tags=["forecasts"])


@router.get("/replenishment/smart")
def get_smart_replenishment_plan(
    auto_create: bool = Query(default=False),
    seller_id: str = Depends(get_current_seller_id),
    db=Depends(get_db_session),
):
    """Profile-aware, lead-time-adjusted smart replenishment plan across active SKUs."""
    return build_smart_replenishment_plan(
        db, seller_id, auto_create_recommendation=auto_create
    )


@router.get("/{sku_id}")
def get_sku_forecast(
    sku_id: str,
    horizon_days: int = Query(default=7, ge=1, le=90),
    seller_id: str = Depends(get_current_seller_id),
    db=Depends(get_db_session),
):
    """Get demand forecast for a SKU with backtest metrics and festival context."""
    result = get_forecast(db, seller_id, sku_id, horizon_days=horizon_days)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{sku_id}/replenishment")
def get_replenishment_plan(
    sku_id: str,
    seller_id: str = Depends(get_current_seller_id),
    db=Depends(get_db_session),
):
    """Get replenishment recommendation for a SKU."""
    result = calculate_replenishment_recommendation(db, seller_id, sku_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
