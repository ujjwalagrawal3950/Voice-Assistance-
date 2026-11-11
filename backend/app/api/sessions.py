"""Previous chat sessions & messages API (ChatGPT-style sidebar)."""

from datetime import datetime, timezone
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_seller_id, get_db_session
from app.models import ChatMessage, ChatSession
from app.schemas import (
    CreateSessionRequest,
    CreateSessionResponse,
    SessionListItem,
    SessionMessageItem,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


def make_title(first_user_message: str) -> str:
    """Deterministically derive a short session title from the first user message."""
    text = first_user_message.strip()
    text = re.sub(r"^(hi|hello|hey|namaste)[\s,!.]*", "", text, flags=re.IGNORECASE)
    text = re.split(r"[.!?\n]", text, maxsplit=1)[0].strip()
    text = text[:50].strip()
    return text or "New chat"


def append_session_exchange(
    db: Session,
    session_id: str,
    user_id: str,
    user_text: str,
    assistant_text: str,
) -> Optional[ChatSession]:
    """Append user/assistant messages cleanly to an existing session and bump updated_at.

    If POST /sessions just inserted `first_message` as the latest user row,
    only the matching assistant reply is appended next.
    Never modifies the session title after creation.
    """
    session = (
        db.query(ChatSession)
        .filter(ChatSession.session_id == session_id, ChatSession.user_id == user_id)
        .first()
    )
    if not session:
        return None

    last_msg = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.sequence_no.desc())
        .first()
    )
    max_seq = last_msg.sequence_no if last_msg else 0

    if not (
        last_msg is not None
        and last_msg.role == "user"
        and last_msg.content.strip() == user_text.strip()
    ):
        max_seq += 1
        db.add(
            ChatMessage(
                session_id=session_id,
                role="user",
                content=user_text,
                sequence_no=max_seq,
            )
        )

    max_seq += 1
    db.add(
        ChatMessage(
            session_id=session_id,
            role="assistant",
            content=assistant_text,
            sequence_no=max_seq,
        )
    )
    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)
    return session


@router.post("", response_model=CreateSessionResponse, status_code=201)
def create_session(
    payload: CreateSessionRequest,
    user_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    """Lazily create a new chat session on the user's first message."""
    title = make_title(payload.first_message)
    now = datetime.now(timezone.utc)
    session = ChatSession(
        user_id=user_id,
        title=title,
        updated_at=now,
    )
    db.add(session)
    db.flush()

    first_msg = ChatMessage(
        session_id=session.session_id,
        role="user",
        content=payload.first_message,
        sequence_no=1,
    )
    db.add(first_msg)
    db.commit()
    db.refresh(session)
    return CreateSessionResponse(session_id=session.session_id, title=session.title or "New chat")


@router.get("", response_model=list[SessionListItem])
def list_sessions(
    user_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    """List up to 50 recent chat sessions for the current user, newest updated first."""
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
        .limit(50)
        .all()
    )


@router.get("/{session_id}/messages", response_model=list[SessionMessageItem])
def get_session_messages(
    session_id: str,
    user_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    """Return ordered messages for a session after verifying ownership (404 otherwise)."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.session_id == session_id)
        .first()
    )
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")

    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.sequence_no.asc())
        .all()
    )

