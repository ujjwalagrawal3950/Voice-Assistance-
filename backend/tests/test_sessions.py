"""Tests for ChatGPT-style previous chats persistence, deterministic title rule, and isolation."""

import time

from fastapi import HTTPException
import pytest

from app.api.sessions import (
    append_session_exchange,
    create_session,
    get_session_messages,
    list_sessions,
    make_title,
)
from app.main import app
from app.models import ChatMessage, ChatSession
from app.schemas import CreateSessionRequest


def test_make_title_deterministic_rules():
    assert make_title("My sales have dropped this month. Can you help?") == "My sales have dropped this month"
    assert make_title("hey, why are my cancellations rising?") == "why are my cancellations rising"
    assert make_title("hi") == "New chat"
    assert make_title("Hello! Stock check please") == "Stock check please"
    assert make_title("Namaste, what is my budget?") == "what is my budget"
    long_msg = "A" * 80 + ". More text"
    assert make_title(long_msg) == "A" * 50


def test_lazy_creation_history_ordering_and_auth_isolation(db_session):
    routes = set(app.openapi()["paths"].keys())
    assert "/sessions" in routes
    assert "/sessions/{session_id}/messages" in routes

    user_a = "user-a-001"
    user_b = "user-b-002"

    # Initial open: empty list, no blank session created
    assert list_sessions(user_id=user_a, db=db_session) == []

    # Send first message in chat 1
    s1 = create_session(
        CreateSessionRequest(first_message="My sales have dropped this month. Can you help?"),
        user_id=user_a,
        db=db_session,
    )
    assert s1.title == "My sales have dropped this month"

    # Simulate assistant completion of turn 1 (seq 1 user already stored -> adds only seq 2 assistant)
    append_session_exchange(
        db=db_session,
        session_id=s1.session_id,
        user_id=user_a,
        user_text="My sales have dropped this month. Can you help?",
        assistant_text="Revenue is down 32.5% driven by 18 stockouts.",
    )
    msgs_s1 = get_session_messages(s1.session_id, user_id=user_a, db=db_session)
    assert [(m.role, m.sequence_no) for m in msgs_s1] == [("user", 1), ("assistant", 2)]

    time.sleep(0.02)

    # Start chat 2 so chat 2 sits above chat 1
    s2 = create_session(
        CreateSessionRequest(first_message="hey, why are my cancellations rising?"),
        user_id=user_a,
        db=db_session,
    )
    assert s2.title == "why are my cancellations rising"

    ordered_before = list_sessions(user_id=user_a, db=db_session)
    assert [s.session_id for s in ordered_before] == [s2.session_id, s1.session_id]

    time.sleep(0.02)

    # Send follow-up inside older chat 1 -> bumps updated_at so s1 floats back to top, keeping original title
    append_session_exchange(
        db=db_session,
        session_id=s1.session_id,
        user_id=user_a,
        user_text="Which SKUs stocked out?",
        assistant_text="Top stockouts include Running Shoes and Cotton Kurti.",
    )

    ordered_after = list_sessions(user_id=user_a, db=db_session)
    assert [s.session_id for s in ordered_after] == [s1.session_id, s2.session_id]
    assert ordered_after[0].title == "My sales have dropped this month"  # Title NEVER regenerated

    msgs_s1_after = get_session_messages(s1.session_id, user_id=user_a, db=db_session)
    assert [(m.role, m.sequence_no) for m in msgs_s1_after] == [
        ("user", 1),
        ("assistant", 2),
        ("user", 3),
        ("assistant", 4),
    ]

    # Cross-user isolation: user_b sees empty list and gets 404 on user_a's session_id
    assert list_sessions(user_id=user_b, db=db_session) == []
    with pytest.raises(HTTPException) as exc_info:
        get_session_messages(s1.session_id, user_id=user_b, db=db_session)
    assert exc_info.value.status_code == 404

