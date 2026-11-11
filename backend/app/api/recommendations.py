"""Recommendations API endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_current_seller_id, get_db_session
from app.models import Recommendation
from app.schemas import RecommendationResponse, RecommendationCreate, ApprovalAction, OutcomeRecord
from app.services.intelligence import get_outcome_track_record

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("")
def list_recommendations(
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
    status: Optional[str] = Query(default=None),
):
    """List recommendations for a seller."""
    query = db.query(Recommendation).filter(Recommendation.seller_id == seller_id)
    if status:
        query = query.filter(Recommendation.approval_status == status)
    rows = query.order_by(Recommendation.created_at.desc()).all()
    return rows


@router.get("/track-record")
def get_recommendations_track_record(
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    """Return historical recommendation outcome win-rates by action type."""
    return get_outcome_track_record(db, seller_id)


@router.get("/{rec_id}", response_model=RecommendationResponse)
def get_recommendation(
    rec_id: str,
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    """Get a single recommendation."""
    rec = (
        db.query(Recommendation)
        .filter(Recommendation.id == rec_id, Recommendation.seller_id == seller_id)
        .first()
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return rec


@router.post("", response_model=RecommendationResponse, status_code=201)
def create_recommendation(
    payload: RecommendationCreate,
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    """Create a draft recommendation requiring seller approval."""
    if payload.seller_id != seller_id:
        raise HTTPException(status_code=403, detail="Cannot create for another seller")
    rec = Recommendation(**payload.model_dump())
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


@router.post("/{rec_id}/approve", response_model=RecommendationResponse)
def approve_recommendation(
    rec_id: str,
    payload: ApprovalAction,
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    """Approve or reject a recommendation."""
    rec = (
        db.query(Recommendation)
        .filter(Recommendation.id == rec_id, Recommendation.seller_id == seller_id)
        .first()
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if payload.action == "approve":
        rec.approval_status = "approved"
    elif payload.action == "reject":
        rec.approval_status = "rejected"
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    db.commit()
    db.refresh(rec)
    return rec


@router.post("/{rec_id}/outcome", response_model=RecommendationResponse)
def record_recommendation_outcome(
    rec_id: str,
    payload: OutcomeRecord,
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    """Record realized outcome (positive/neutral/negative) to weight future confidence."""
    if payload.outcome_status not in ("positive", "neutral", "negative"):
        raise HTTPException(status_code=400, detail="outcome_status must be positive, neutral, or negative")
    rec = (
        db.query(Recommendation)
        .filter(Recommendation.id == rec_id, Recommendation.seller_id == seller_id)
        .first()
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    rec.execution_status = "executed"
    rec.outcome_status = payload.outcome_status
    if payload.actual_units_ordered is not None:
        rec.actual_units_ordered = payload.actual_units_ordered
    if payload.actual_revenue_delta_pct is not None:
        rec.actual_revenue_delta_pct = payload.actual_revenue_delta_pct
    if payload.actual_margin_pct is not None:
        rec.actual_margin_pct = payload.actual_margin_pct
    if payload.outcome_notes is not None:
        rec.outcome_notes = payload.outcome_notes
    rec.outcome_recorded_at = datetime.utcnow()
    db.commit()
    db.refresh(rec)
    return rec
