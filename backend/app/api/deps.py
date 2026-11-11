"""API dependencies."""

from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.config import settings


def get_db_session() -> Session:
    return next(get_db())


def get_current_seller_id(
    x_seller_id: Optional[str] = Header(default=None, alias="X-Seller-Id"),
) -> str:
    """Return the authenticated seller ID.

    For the MVP prototype, the seller ID comes from a secure header.
    In production this would be derived from a validated session/JWT.
    Never trust a client-supplied seller_id when authenticated identity can determine it.
    """
    seller_id = x_seller_id or settings.seller_id
    if not seller_id:
        raise HTTPException(status_code=401, detail="Seller identity not established")
    return seller_id
