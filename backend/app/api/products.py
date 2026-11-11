"""Product / SKU API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_seller_id, get_db_session
from app.models import Product, DailyPerformance
from app.schemas import ProductResponse, ProductCreate, DailyPerformanceResponse

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=List[ProductResponse])
def list_products(
    category: Optional[str] = Query(default=None),
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    query = db.query(Product).filter(Product.seller_id == seller_id)
    if category:
        query = query.filter(Product.category == category)
    return query.all()


@router.get("/{sku_id}", response_model=ProductResponse)
def get_product(
    sku_id: str,
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    product = db.query(Product).filter(Product.id == sku_id, Product.seller_id == seller_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("", response_model=ProductResponse, status_code=201)
def create_product(
    payload: ProductCreate,
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    # Enforce that the seller_id in the body matches the authenticated seller
    if payload.seller_id != seller_id:
        raise HTTPException(status_code=403, detail="Cannot create product for another seller")
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product
