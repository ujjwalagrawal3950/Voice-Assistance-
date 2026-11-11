"""Inventory health API endpoint."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_seller_id, get_db_session
from app.models import Product
from app.services.kpi import calculate_stock_cover_days, calculate_inventory_value
from datetime import date

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("/health")
def get_inventory_health(
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    """Return inventory health: stockouts, low cover, dead stock candidates."""
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
                    "current_stock": p.current_stock,
                }
            )
        elif cover["value"] is not None and cover["value"] < 7:
            low_cover.append(
                {
                    "sku_id": p.id,
                    "sku_code": p.sku_code,
                    "title": p.title,
                    "cover_days": cover["value"],
                    "current_stock": p.current_stock,
                }
            )
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

    inventory = calculate_inventory_value(db, seller_id)

    return {
        "seller_id": seller_id,
        "stockouts": stockouts,
        "low_cover": low_cover,
        "dead_stock": dead_stock,
        "stockout_count": len(stockouts),
        "low_cover_count": len(low_cover),
        "dead_stock_count": len(dead_stock),
        "inventory_value_cost": inventory["value_at_cost"],
        "inventory_value_selling": inventory["value_at_selling"],
        "data_status": "calculated",
    }
