"""Virtual KAM Memory Package.

Deterministic, seller-scoped memory layer for the Virtual KAM agent.

Provides:
- Deterministic data model (MemoryItem)
- Pluggable storage (InMemoryStore, VectorStoreAdapter)
- ContextManager for building seller-aware contexts from memory
- LLM-free deterministic fact extraction for recommendation memory
- Typed tools for agentic memory read/write (search_memory, remember_fact)

Design principles:
- Deterministic: identical inputs produce identical memory writes/reads
- Seller-scoped: every record is keyed by seller_id
- Timeout-safe: every storage call wraps asyncio.wait_for with a timeout
- Non-blocking: memory calls never block the agent response path

"""

from app.memory.config import MemorySettings, MemorySettingsError
from app.memory.store import (
    MemoryItem,
    MemoryStore,
    InMemoryStore,
    VectorStoreAdapter,
    create_memory_store,
)
from app.memory.context_manager import ContextManager, build_context_for_agent
from app.memory.extractor import extract_facts
from app.memory.tools import get_memory_tools, get_memory_tool_descriptions

__all__ = [
    "MemoryItem",
    "MemoryStore",
    "InMemoryStore",
    "VectorStoreAdapter",
    "create_memory_store",
    "ContextManager",
    "build_context_for_agent",
    "extract_facts",
    "MemorySettings",
    "MemorySettingsError",
]
