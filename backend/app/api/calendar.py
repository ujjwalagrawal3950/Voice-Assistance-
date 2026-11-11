"""Festival calendar API endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date

from app.api.deps import get_current_seller_id, get_db_session
from app.models import CalendarEvent, Seller

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("/festival")
def get_festival_calendar(
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    """Return upcoming Indian festival/regional events relevant to the seller."""
    seller = db.query(Seller).filter(Seller.id == seller_id).first()
    seller_state = seller.state if seller else None

    today = date.today()
    events = (
        db.query(CalendarEvent)
        .filter(CalendarEvent.end_date >= today)
        .order_by(CalendarEvent.start_date)
        .all()
    )

    relevant = []
    for e in events:
        if e.geography and e.geography not in ("India", seller_state or ""):
            continue
        relevant.append(
            {
                "event_name": e.event_name,
                "event_type": e.event_type,
                "start_date": e.start_date.isoformat(),
                "end_date": e.end_date.isoformat(),
                "geography": e.geography,
                "shopping_lead_in_days": e.shopping_lead_in_days,
                "category_relevance": e.category_relevance,
                "confidence": e.confidence,
                "source_url": e.source_url,
                "data_status": "observed" if e.confidence == "verified" else "scenario",
            }
        )

    return {
        "seller_id": seller_id,
        "seller_state": seller_state,
        "upcoming_events": relevant,
        "data_status": "observed",
    }
