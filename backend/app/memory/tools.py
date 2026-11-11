"""Typed tools for the Virtual KAM memory system.

These tools give the LLM agent read/write access to the seller's
persistent memory store. They follow the same conventions as the
existing tool catalogue in backend/app/agent/tools.py.

All tools are async (async def) because they call async store methods.
The agent service's _execute_tool handles both sync and async tools.
"""

from __future__ import annotations

from typing import Any

from app.memory.store import MemoryItem, create_memory_store
from app.memory.context_manager import get_memory_manager


# ── Tool: get_seller_memory (read) ──────────────────────────────────────

async def search_memory(
    seller_id: str,
    query: str,
    top_k: int = 5,
) -> dict[str, Any]:
    """Search the seller's persistent memory for relevant past facts.

    Use this when the seller refers to something discussed before, or when
    you need to recall a past recommendation, stockout, or preference.

    Returns structured memory items with confidence scores.
    """
    manager = get_memory_manager()
    try:
        items = await manager.store.recall(
            seller_id=seller_id, query=query, top_k=top_k
        )
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Memory recall failed: {exc}"}

    items = items or []
    return {
        "seller_id": seller_id,
        "query": query,
        "count": len(items),
        "items": [
            {
                "id": item.id,
                "content": item.content,
                "kind": item.kind,
                "confidence": item.confidence,
                "source": item.source,
                "created_at": item.created_at,
            }
            for item in items
        ],
    }


# ── Tool: remember_fact (write) ─────────────────────────────────────────

async def remember_fact(
    seller_id: str,
    content: str,
    kind: str = "fact",
    confidence: float | None = None,
    source: str = "user",
) -> dict[str, Any]:
    """Persist a fact or preference to the seller's long-term memory.

    Use this when the seller states a goal, preference, constraint, or
    important fact that should be remembered across sessions.

    Returns the created recommendation record id.
    """
    from app.memory.store import MemoryItem

    manager = get_memory_manager()
    try:
        item = MemoryItem(
            seller_id=seller_id,
            content=content,
            kind=kind,
            confidence=confidence,
            source=source,
        )
        await manager.store.upsert(item)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Memory write failed: {exc}"}

    return {
        "id": item.id,
        "seller_id": seller_id,
        "content": content,
        "kind": kind,
        "status": "stored",
    }


# ── Tool registry ───────────────────────────────────────────────────────

MEMORY_TOOL_REGISTRY = {
    "search_memory": search_memory,
    "remember_fact": remember_fact,
}

MEMORY_TOOL_DESCRIPTIONS = {
    "search_memory": "Search the seller's past conversations and remembered facts. Use this when the seller refers to something discussed before, or when you need to recall a past recommendation, stockout, or preference.",
    "remember_fact": "Persist a seller fact, preference, or constraint to long-term memory. Use this when the seller states a goal, budget, margin target, risk tolerance, or any fact worth remembering for future conversations.",
}


def get_memory_tools() -> dict[str, callable]:
    """Return the memory tool registry."""
    return MEMORY_TOOL_REGISTRY


def get_memory_tool_descriptions() -> dict[str, str]:
    """Return descriptions of memory tools for system prompt injection."""
    return MEMORY_TOOL_DESCRIPTIONS
