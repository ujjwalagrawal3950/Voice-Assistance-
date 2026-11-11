"""Proactive KAM alerts and periodic digest endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_seller_id, get_db_session
from app.models import ProactiveAlert
from app.schemas import ProactiveAlertResponse
from app.services.intelligence import generate_proactive_alerts

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[ProactiveAlertResponse])
def list_alerts(
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    """Return active proactive alerts (generates initial scan if none exist yet)."""
    existing = (
        db.query(ProactiveAlert)
        .filter(ProactiveAlert.seller_id == seller_id, ProactiveAlert.dismissed == False)  # noqa: E712
        .order_by(ProactiveAlert.created_at.desc())
        .all()
    )
    if existing:
        return existing
    generate_proactive_alerts(db, seller_id, channel="in_app", persist=True)
    return (
        db.query(ProactiveAlert)
        .filter(ProactiveAlert.seller_id == seller_id, ProactiveAlert.dismissed == False)  # noqa: E712
        .order_by(ProactiveAlert.created_at.desc())
        .all()
    )


@router.post("/run-digest", response_model=list[ProactiveAlertResponse])
def run_digest_now(
    channel: str = Query(default="in_app"),
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    """Manually trigger the proactive KAM diagnosis digest for a seller."""
    generate_proactive_alerts(db, seller_id, channel=channel, persist=True)
    return (
        db.query(ProactiveAlert)
        .filter(ProactiveAlert.seller_id == seller_id, ProactiveAlert.dismissed == False)  # noqa: E712
        .order_by(ProactiveAlert.created_at.desc())
        .all()
    )


@router.post("/{alert_id}/dismiss", response_model=ProactiveAlertResponse)
def dismiss_alert(
    alert_id: str,
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    """Dismiss an alert once reviewed by the seller."""
    alert = (
        db.query(ProactiveAlert)
        .filter(ProactiveAlert.id == alert_id, ProactiveAlert.seller_id == seller_id)
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.dismissed = True
    alert.is_read = True
    db.commit()
    db.refresh(alert)
    return alert

