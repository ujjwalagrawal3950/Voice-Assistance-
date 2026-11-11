"""Seller API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_seller_id, get_db_session
from app.config import settings
from app.database import SessionLocal
from app.models import Seller
from app.schemas import SellerResponse, SellerUpdate, SellerCreate

router = APIRouter(prefix="/api/seller", tags=["seller"])


@router.get("/profile", response_model=SellerResponse)
def get_seller_profile(seller_id: str = Depends(get_current_seller_id), db: Session = Depends(get_db_session)):
    seller = db.query(Seller).filter(Seller.id == seller_id).first()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    return seller


@router.patch("/profile", response_model=SellerResponse)
def update_seller_profile(
    payload: SellerUpdate,
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    seller = db.query(Seller).filter(Seller.id == seller_id).first()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(seller, field, value)
    db.commit()
    db.refresh(seller)
    return seller
