"""Data model and storage for Virtual KAM memory.

Provides:
- MemoryItem: typed record of a remembered fact/turn
- MemoryStore: abstract protocol for persistence
- InMemoryStore: in-memory, deterministic implementation (default)
- VectorStoreAdapter: placeholder for pgvector/Chroma/Qdrant backends

All store methods are async and seller-scoped. Missing data is represented as
missing, never as empty/zero defaults.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable


class MemoryItem:
    """A single remembered fact or turn.

    Attributes:
        id: Unique identifier (UUID hex).
        seller_id: Owning seller (enforced at write time).
        content: The remembered text.
        kind: Category — "observed", "calculated", "forecast", "scenario",
              "preference", "fact", "dead_stock", "stockout", etc.
        source: Where this fact came from ("user", "tool", "diagnosis", etc.)
        confidence: Optional confidence score 0.0-1.0.
        metadata: Arbitrary JSON-serializable metadata.
        created_at: ISO-8601 timestamp when first stored.
        last_accessed_at: ISO-8601 timestamp of last read.
        expiry: Optional ISO-8601 date when this memory expires.
        embedding: Optional embedding vector (provider-specific).
    """

    def __init__(
        self,
        *,
        id: str | None = None,
        seller_id: str,
        content: str,
        kind: str = "fact",
        source: str = "user",
        confidence: float | None = None,
        metadata: dict | None = None,
        created_at: str | None = None,
        last_accessed_at: str | None = None,
        expiry: str | None = None,
        embedding: list[float] | None = None,
    ):
        self.id = id or f"mem-{uuid.uuid4().hex[:12]}"
        self.seller_id = seller_id
        self.content = content
        self.kind = kind
        self.source = source
        self.confidence = confidence
        self.metadata = metadata or {}
        self.created_at = created_at or _now_iso()
        self.last_accessed_at = last_accessed_at or self.created_at
        self.expiry = expiry
        self.embedding = embedding

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "seller_id": self.seller_id,
            "content": self.content,
            "kind": self.kind,
            "source": self.source,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "last_accessed_at": self.last_accessed_at,
            "expiry": self.expiry,
            "embedding": self.embedding,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryItem":
        return cls(
            id=data.get("id"),
            seller_id=data["seller_id"],
            content=data["content"],
            kind=data.get("kind", "fact"),
            source=data.get("source", "user"),
            confidence=data.get("confidence"),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at"),
            last_accessed_at=data.get("last_accessed_at"),
            expiry=data.get("expiry"),
            embedding=data.get("embedding"),
        )


class MemoryStore(Protocol):
    """Abstract interface for seller-scoped memory persistence.

    Implementations must be seller-scoped: every record carries a seller_id
    and only that seller may read/write it. Missing data is represented as
    missing, never as empty/zero defaults.
    """

    async def upsert(self, item: MemoryItem) -> str:
        """Store or update a memory item. Returns the item id."""
        ...

    async def recall(
        self,
        seller_id: str,
        query: str,
        top_k: int = 5,
        timeout_ms: int = 1200,
    ) -> list[MemoryItem]:
        """Retrieve up to top_k most relevant memory items for a seller.

        Must complete within timeout_ms or raise TimeoutError.
        """
        ...

    async def forget(self, seller_id: str, item_id: str) -> bool:
        """Delete a single memory item by id. Returns True if deleted."""
        ...

    async def forget_all(self, seller_id: str) -> int:
        """Delete all memory items for a seller. Returns count deleted."""
        ...

    async def count(self, seller_id: str) -> int:
        """Return the number of stored items for a seller."""
        ...

    async def health(self) -> dict:
        """Return health status of the store."""
        ...


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


class InMemoryStore(MemoryStore):
    """In-memory, deterministic implementation of MemoryStore.

    Suitable for local development and testing. All data is held in
    memory and lost on process restart. Suitable for single-worker
    prototypes.
    """

    def __init__(self) -> None:
        self._store: dict[str, list[MemoryItem]] = {}

    async def upsert(self, item: MemoryItem) -> str:
        rows = self._store.setdefault(item.seller_id, [])
        # Replace existing id if present
        for i, existing in enumerate(rows):
            if existing.id == item.id:
                rows[i] = item
                return item.id
        rows.append(item)
        return item.id

    async def recall(
        self,
        seller_id: str,
        query: str,
        top_k: int = 5,
        timeout_ms: int = 1200,
    ) -> list[MemoryItem]:
        rows = self._store.get(seller_id, [])
        # Simple keyword overlap scoring for in-memory
        query_terms = set(query.lower().split())
        scored: list[tuple[float, MemoryItem]] = []
        for item in rows:
            score = sum(1 for term in query_terms if term in item.content.lower())
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        result = [item for _, item in scored[:top_k]]
        # Mark accessed
        for item in result:
            item.last_accessed_at = _now_iso()
        return result

    async def forget(self, seller_id: str, item_id: str) -> bool:
        rows = self._store.get(seller_id, [])
        for i, item in enumerate(rows):
            if item.id == item_id:
                rows.pop(i)
                return True
        return False

    async def forget_all(self, seller_id: str) -> int:
        rows = self._store.pop(seller_id, [])
        return len(rows)

    async def count(self, seller_id: str) -> int:
        return len(self._store.get(seller_id, []))

    async def health(self) -> dict:
        total = sum(len(rows) for rows in self._store.values())
        return {
            "store": "in_memory",
            "status": "ok",
            "total_items": total,
            "sellers": len(self._store),
        }


class VectorStoreAdapter(MemoryStore):
    """Placeholder adapter for vector stores (pgvector, Chroma, Qdrant, etc.).

    The concrete implementation depends on the chosen vector store and
    embedding model. This class provides the interface shape; concrete
    implementations should subclass and implement the async methods.

    Raises NotImplementedError for all methods until a concrete subclass
    implements them.
    """

    async def upsert(self, item: MemoryItem) -> str:
        raise NotImplementedError("VectorStoreAdapter is a base class; subclass required.")

    async def recall(
        self,
        seller_id: str,
        query: str,
        top_k: int = 5,
        timeout_ms: int = 1200,
    ) -> list[MemoryItem]:
        raise NotImplementedError("VectorStoreAdapter is a base class; subclass required.")

    async def forget(self, seller_id: str, item_id: str) -> bool:
        raise NotImplementedError("VectorStoreAdapter is a base class; subclass required.")

    async def forget_all(self, seller_id: str) -> int:
        raise NotImplementedError("VectorStoreAdapter is a base class; subclass required.")

    async def count(self, seller_id: str) -> int:
        raise NotImplementedError("VectorStoreAdapter is a base class; subclass required.")

    async def health(self) -> dict:
        return {"store": "vector", "status": "not_implemented"}


def create_memory_store(backend: str = "in_memory") -> MemoryStore:
    """Factory to create a store instance by backend name."""
    if backend == "in_memory":
        return InMemoryStore()
    if backend == "vector":
        return VectorStoreAdapter()
    raise ValueError(f"Unknown memory store backend: {backend}")


def store_conversation_turn(
    *,
    seller_id: str,
    conversation_id: str,
    turn_number: int,
    user_message: str,
    assistant_response: str,
    tool_results: dict[str, Any] | None = None,
    db=None,
):
    """Extract facts from a conversation turn and persist a ConversationMemory row."""
    from app.database import SessionLocal
    from app.memory.extractor import extract_facts_from_turn
    from app.models import ConversationMemory

    extracted = extract_facts_from_turn(
        user_message=user_message,
        assistant_response=assistant_response,
        tool_results=tool_results or {},
    )
    own_session = db is None
    session = db or SessionLocal()
    try:
        row = ConversationMemory(
            seller_id=seller_id,
            conversation_id=conversation_id,
            turn_number=turn_number,
            user_message=user_message,
            assistant_response=assistant_response,
            problem_summary=extracted["problem_summary"],
            solution_summary=extracted["solution_summary"],
            key_takeaway=extracted["key_takeaway"],
            related_sku_ids=extracted["related_sku_ids"],
            confidence=extracted["confidence"],
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row
    finally:
        if own_session:
            session.close()


def recall_conversation_memories(
    seller_id: str,
    query: str = "",
    limit: int = 5,
    db=None,
) -> list[dict[str, Any]]:
    """Retrieve relevant historical ConversationMemory records for a seller."""
    from app.database import SessionLocal
    from app.models import ConversationMemory

    own_session = db is None
    session = db or SessionLocal()
    try:
        rows = (
            session.query(ConversationMemory)
            .filter(ConversationMemory.seller_id == seller_id)
            .order_by(ConversationMemory.created_at.desc())
            .limit(40)
            .all()
        )
        if not rows:
            return []

        terms = {w.strip(".,?!:;").lower() for w in query.split() if len(w.strip(".,?!:;")) >= 3}
        scored: list[tuple[float, Any]] = []
        for idx, r in enumerate(rows):
            haystack = " ".join(
                filter(None, [r.user_message, r.problem_summary, r.solution_summary, r.key_takeaway, r.related_sku_ids])
            ).lower()
            overlap = sum(1.0 for t in terms if t in haystack)
            recency_bonus = max(0.0, 0.5 - idx * 0.05)
            scored.append((overlap + recency_bonus, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        chosen = [r for _, r in scored[:limit]]
        return [
            {
                "id": r.id,
                "conversation_id": r.conversation_id,
                "turn_number": r.turn_number,
                "user_message": r.user_message,
                "problem_summary": r.problem_summary,
                "solution_summary": r.solution_summary,
                "key_takeaway": r.key_takeaway,
                "related_sku_ids": r.related_sku_ids,
                "confidence": r.confidence,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in chosen
        ]
    finally:
        if own_session:
            session.close()


def load_session_history(
    seller_id: str,
    conversation_id: str,
    limit_turns: int = 10,
    db=None,
) -> list[dict[str, str]]:
    """Rehydrate past chat turns for a given conversation_id from SQLite."""
    from app.database import SessionLocal
    from app.models import ConversationMemory

    own_session = db is None
    session = db or SessionLocal()
    try:
        rows = (
            session.query(ConversationMemory)
            .filter(
                ConversationMemory.seller_id == seller_id,
                ConversationMemory.conversation_id == conversation_id,
            )
            .order_by(ConversationMemory.turn_number.asc(), ConversationMemory.created_at.asc())
            .all()
        )
        history: list[dict[str, str]] = []
        for r in rows[-limit_turns:]:
            history.append({"role": "user", "content": r.user_message})
            history.append({"role": "assistant", "content": r.assistant_response})
        return history
    finally:
        if own_session:
            session.close()


def format_memory_context(memories: list[dict[str, Any]]) -> str:
    """Format recalled ConversationMemory entries into prompt text."""
    if not memories:
        return "No prior conversation memories recorded yet for this seller."
    lines: list[str] = []
    for m in memories:
        when = (m.get("created_at") or "")[:10] or "earlier"
        skus = f" | SKUs: {m['related_sku_ids']}" if m.get("related_sku_ids") else ""
        lines.append(
            f"- [{when}, turn {m.get('turn_number', 1)}] Problem: {m.get('problem_summary')} "
            f"| Action/Solution: {m.get('solution_summary')} | Takeaway: {m.get('key_takeaway')}{skus}"
        )
    return "\n".join(lines)
