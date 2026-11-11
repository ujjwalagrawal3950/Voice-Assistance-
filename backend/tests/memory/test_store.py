"""Unit tests for the Virtual KAM memory store implementations.

Tests cover:
- InMemoryStore upsert/retrieve/forget
- Duplicate ID handling (update in place)
- MemoryItem serialization/deserialization
- Store health check
"""

import pytest

from app.memory.store import MemoryItem, MemoryStore, InMemoryStore, VectorStoreAdapter, create_memory_store


# ── Helpers ──────────────────────────────────────────────────────────

def _make_item(seller_id: str = "seller-1", content: str = "test fact", kind: str = "fact") -> MemoryItem:
    return MemoryItem(
        seller_id=seller_id,
        content=content,
        kind=kind,
        source="test",
        confidence=0.9,
    )


# ── MemoryItem ──────────────────────────────────────────────────────

def test_memory_item_to_dict_roundtrip():
    item = MemoryItem(
        id="mem-1",
        seller_id="seller-1",
        content="Test fact content",
        kind="fact",
        source="user",
        confidence=0.9,
        metadata={"key": "value"},
        expiry="2026-12-01",
    )
    d = item.to_dict()
    assert d["id"] == "mem-1"
    assert d["seller_id"] == "seller-1"
    assert d["content"] == "Test fact content"
    assert d["kind"] == "fact"
    assert d["source"] == "user"
    assert d["confidence"] == 0.9
    assert d["metadata"] == {"key": "value"}
    assert d["expiry"] == "2026-12-01"

    # Round-trip
    item2 = MemoryItem.from_dict(d)
    assert item2.id == item.id
    assert item2.seller_id == item.seller_id
    assert item2.content == item.content
    assert item2.kind == item.kind
    assert item2.source == item.source
    assert item2.confidence == item.confidence
    assert item2.metadata == item.metadata
    assert item2.expiry == item.expiry


# ── InMemoryStore ───────────────────────────────────────────────────

def test_in_memory_store_upsert_and_recall():
    store = InMemoryStore()
    item = _make_item(seller_id="seller-1", content="Test fact content", kind="fact")

    import asyncio
    asyncio.run(store.upsert(item))

    results = asyncio.run(store.recall(seller_id="seller-1", query="test fact", top_k=5))
    assert len(results) == 1
    assert results[0].id == item.id
    assert results[0].content == "Test fact content"


def test_in_memory_store_upsert_updates_existing():
    store = InMemoryStore()
    item1 = MemoryItem(seller_id="seller-1", sku_id=None, content="Original content", kind="fact", source="test")
    item2 = MemoryItem(id=item1.id, seller_id="seller-1", sku_id=None, content="Updated content", kind="fact", source="test")

    import asyncio
    asyncio.run(store.upsert(item1))
    asyncio.run(store.upsert(item2))

    results = asyncio.run(store.recall(seller_id="seller-1", query="content", top_k=5))
    assert len(results) == 1
    assert results[0].content == "Updated content"


def test_in_memory_store_forget():
    store = InMemoryStore()
    item = _make_item(seller_id="seller-1", content="To be deleted", kind="fact")

    import asyncio
    asyncio.run(store.upsert(item))

    # Verify it exists
    results = asyncio.run(store.recall(seller_id="seller-1", query="deleted", top_k=5))
    assert len(results) == 1

    # Delete it
    deleted = asyncio.run(store.forget(seller_id="seller-1", item_id=item.id))
    assert deleted is True

    # Verify it's gone
    results = asyncio.run(store.recall(seller_id="seller-1", query="deleted", top_k=5))
    assert len(results) == 0


def test_in_memory_store_forget_nonexistent():
    store = InMemoryStore()
    deleted = asyncio.run(store.forget(seller_id="seller-1", item_id="nonexistent"))
    assert deleted is False


def test_in_memory_store_forget_all():
    store = InMemoryStore()
    item1 = _make_item(seller_id="seller-1", content="Item 1", kind="fact")
    item2 = _make_item(seller_id="seller-1", content="Item 2", kind="fact")
    item3 = _make_item(seller_id="seller-2", content="Item 3", kind="fact")

    import asyncio
    asyncio.run(store.upsert(item1))
    asyncio.run(store.upsert(item2))
    asyncio.run(store.upsert(item3))

    # Forget all for seller-1
    count = asyncio.run(store.forget_all(seller_id="seller-1"))
    assert count == 2

    # Only seller-2's data remains
    results = asyncio.run(store.recall(seller_id="seller-1", query="", top_k=5))
    assert len(results) == 0
    results = asyncio.run(store.recall(seller_id="seller-2", query="Item 3", top_k=5))
    assert len(results) == 1


def test_in_memory_store_count():
    store = InMemoryStore()
    item1 = _make_item(seller_id="seller-1", content="Item 1", kind="fact")
    item2 = _make_item(seller_id="seller-1", content="Item 2", kind="fact")
    item3 = _make_item(seller_id="seller-2", content="Item 3", kind="fact")

    import asyncio
    asyncio.run(store.upsert(item1))
    asyncio.run(store.upsert(item2))
    asyncio.run(store.upsert(item3))

    assert asyncio.run(store.count(seller_id="seller-1")) == 2
    assert asyncio.run(store.count(seller_id="seller-2")) == 1
    assert asyncio.run(store.count(seller_id="seller-3")) == 0


def test_in_memory_store_health():
    store = InMemoryStore()
    health = asyncio.run(store.health())
    assert health["store"] == "in_memory"
    assert health["status"] == "ok"


# ── Factory ───────────────────────────────────────────────────────

def test_create_memory_store_in_memory():
    store = create_memory_store("in_memory")
    assert isinstance(store, InMemoryStore)


def test_create_memory_store_vector():
    store = create_memory_store("vector")
    assert isinstance(store, VectorStoreAdapter)


def test_create_memory_store_unknown():
    from app.memory.store import create_memory_store
    try:
        create_memory_store("invalid_backend")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


# ── VectorStoreAdapter (placeholder) ──────────────────────────────

def test_vector_store_adapter_placeholder():
    store = VectorStoreAdapter()
    # All methods should raise NotImplementedError
    import asyncio

    async def test_all():
        try:
            await store.upsert(MemoryItem(seller_id="s1", sku_id=None, content="test", kind="fact", source="test"))
            assert False, "Should have raised NotImplementedError"
        except NotImplementedError:
            pass

        try:
            await store.recall(seller_id="s1", query="test", top_k=5)
            assert False, "Should have raised NotImplementedError"
        except NotImplementedError:
            pass

        try:
            await store.forget(seller_id="s1", item_id="id1")
            assert False, "Should have raised NotImplementedError"
        except NotImplementedError:
            pass

        try:
            await store.forget_all(seller_id="s1")
            assert False, "Should have raised NotImplementedError"
        except NotImplementedError:
            pass

        try:
            await store.count(seller_id="s1")
            assert False, "Should have raised NotImplementedError"
        except NotImplementedError:
            pass

        # health should work
        health = await store.health()
        assert health["store"] == "vector"
        assert health["status"] == "not_implemented"

    import asyncio
    asyncio.run(test_all())
