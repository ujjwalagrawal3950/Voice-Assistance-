"""Unit tests for the Virtual KAM memory tools."""

import pytest

from app.memory.tools import (
    search_memory,
    remember_fact,
    get_memory_tools,
    get_memory_tool_descriptions,
    MEMORY_TOOL_REGISTRY,
    MEMORY_TOOL_DESCRIPTIONS,
)


def test_memory_tools_registry():
    """The memory tool registry contains expected tools."""
    assert "search_memory" in MEMORY_TOOL_REGISTRY
    assert "remember_fact" in MEMORY_TOOL_REGISTRY


def test_memory_tool_descriptions():
    """Tool descriptions are non-empty and descriptive."""
    descs = get_memory_tool_descriptions()
    assert "search_memory" in descs
    assert "remember_fact" in descs
    assert len(descs["search_memory"]) > 10
    assert len(descs["remember_fact"]) > 10


def test_get_memory_tools():
    """get_memory_tools returns the registry."""
    tools = get_memory_tools()
    assert "search_memory" in tools
    assert "remember_fact" in tools


def test_search_memory_returns_empty_for_empty_store():
    """search_memory returns empty results when no data exists."""
    import asyncio

    result = asyncio.run(
        search_memory(seller_id="seller-1", query="anything", top_k=5)
    )
    assert "seller_id" in result
    assert result["seller_id"] == "seller-1"
    assert result["query"] == "anything"
    assert result["count"] == 0
    assert result["items"] == []


def test_remember_fact_and_search():
    """remember_fact stores and search_memory retrieves."""
    import asyncio

    # First, remember a fact
    result = asyncio.run(
        remember_fact(
            seller_id="seller-1",
            content="Seller prefers not to restock Basmati Rice before Diwali",
            kind="preference",
            confidence=0.9,
            source="user",
        )
    )
    assert "id" in result
    assert result["seller_id"] == "seller-1"
    assert result["content"] == "Seller prefers not to restock Basmati Rice before Diwali"
    assert result["kind"] == "preference"
    assert result["status"] == "stored"

    # Then, search for it
    result2 = asyncio.run(
        search_memory(seller_id="seller-1", query="Basmati Rice restock", top_k=5)
    )
    assert result2["seller_id"] == "seller-1"
    assert result2["query"] == "Basmati Rice restock"
    assert result2["count"] >= 1
    # Find our stored fact in results
    found = any("Basmati Rice" in item["content"] for item in result2["items"])
    assert found, f"Expected to find Basmati Rice fact in results: {result2['items']}"


def test_remember_fact_with_confidence():
    """remember_fact stores confidence when provided."""
    import asyncio

    result = asyncio.run(
        remember_fact(
            seller_id="seller-1",
            content="Target margin is 25%",
            kind="margin",
            confidence=0.95,
            source="user",
        )
    )
    assert result["id"] is not None
    assert result["content"] == "Target margin is 25%"
    assert result["kind"] == "margin"


def test_search_memory_top_k_limits_results():
    """search_memory respects top_k parameter."""
    import asyncio

    # Store multiple facts
    for i in range(5):
        asyncio.run(
            remember_fact(
                seller_id="seller-1",
                content=f"Fact number {i}",
                kind="fact",
                confidence=0.5,
            )
        )

    result = asyncio.run(
        search_memory(seller_id="seller-1", query="fact", top_k=2)
    )
    assert result["count"] <= 2
    assert len(result["items"]) <= 2


def test_search_memory_is_seller_scoped():
    """search_memory only returns results for the requesting seller."""
    import asyncio

    # Store facts for two different sellers
    asyncio.run(
        remember_fact(
            seller_id="seller-1",
            content="Seller 1 fact",
            kind="fact",
            confidence=0.9,
        )
    )
    asyncio.run(
        remember_fact(
            seller_id="seller-2",
            content="Seller 2 fact",
            kind="fact",
            confidence=0.9,
        )
    )

    result_s1 = asyncio.run(
        search_memory(seller_id="seller-1", query="fact", top_k=5)
    )
    result_s2 = asyncio.run(
        search_memory(seller_id="seller-2", query="fact", top_k=5)
    )

    assert result_s1["count"] == 1
    assert result_s2["count"] == 1
    assert result_s1["items"][0]["content"] == "Seller 1 fact"
    assert result_s2["items"][0]["content"] == "Seller 2 fact"
