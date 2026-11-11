"""ContextManager: deterministic context assembly for the Virtual KAM agent.

Responsibilities:
1. Build a structured LLM prompt context from seller profile, tool results,
   and retrieved memory items.
2. Retrieve memory deterministically with a hard timeout (default 1200ms).
   On timeout, proceed without memory (graceful degradation).
3. Merge retrieved memory with existing chat history without duplicating
   facts already present in the context.
4. Trim/organize context to fit token limits: truncate oldest non-system
   turns first, summarize remaining overflow into a single summary block.
5. Persist durable facts from each turn back to the store (capture_turn).
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.memory.config import MemorySettings, memory_settings
from app.memory.extractor import extract_facts
from app.memory.store import MemoryItem, MemoryStore, create_memory_store

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class ContextManager:
    """Builds and maintains the KAM agent's context from memory + live data.

    The context is assembled deterministically:
    - System prompt (seller profile + agent role)
    - Recalled memory (observed facts, past recommendations, dead stock, etc.)
    - Current tool results
    - Recent conversation history (bounded)
    - A concise summary of older truncated turns (if any)

    Tool calls are guaranteed non-blocking: memory retrieval uses
    asyncio.wait_for with a configurable timeout; on timeout the agent
    proceeds without memory.
    """

    def __init__(
        self,
        store: MemoryStore | None = None,
        settings: MemorySettings | None = None,
    ):
        self.store = store or create_memory_store(
            settings.backend if settings else "in_memory"
        )
        self.settings = settings or MemorySettings()
        self._recall_cache: dict[str, tuple[list[MemoryItem], float]] = {}

    # ── Public API ──────────────────────────────────────────────────

    async def build_context(
        self,
        seller_id: str,
        seller_profile: dict,
        tool_results: dict[str, Any],
        conversation_history: list[dict[str, str]],
        user_message: str,
        channel: str = "text",
    ) -> dict:
        """Build the full KAM agent context for a seller turn.

        Returns a dict with:
          - system_prompt: str
          - conversation_history: list[dict]
          - memory_used: list[str]  (ids of memory items referenced)
          - memory_count: int
        """
        # Step 1: Retrieve memory deterministically (with timeout)
        memory_items = await self._retrieve_memory(seller_id, user_message)

        # Step 2: Build system prompt from seller profile + memory
        system_prompt = self._build_system_prompt(
            seller_profile, tool_results, memory_items, channel
        )

        # Step 3: Assemble conversation history with memory context injected
        history = self._build_conversation_history(
            conversation_history, memory_items
        )

        # Step 4: Enforce token budget (truncate + summarize)
        history = self._truncate_and_summarize(history, system_prompt)

        return {
            "system_prompt": system_prompt,
            "conversation_history": history,
            "memory_used": [item.id for item in memory_items],
            "memory_count": len(memory_items),
            "tool_results": tool_results,
        }

    async def capture_turn(
        self,
        seller_id: str,
        user_message: str,
        assistant_response: str,
        tool_results: dict[str, Any] | None = None,
    ) -> list[str]:
        """Persist durable facts from a completed turn.

        Extracts durable facts via the extractor, stores them as memory items,
        and returns the list of stored item ids.
        """
        if not self.settings or not self.settings.enabled:
            return []

        # Only store if capture mode is not "off"
        if self.settings.capture_mode == "off":
            return []

        try:
            extraction = extract_facts(
                user_message=user_message,
                assistant_response=assistant_response,
                tool_results=tool_results or {},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Fact extraction failed: %s", exc)
            return []

        stored_ids: list[str] = []
        for fact in extraction.facts:
            try:
                item = MemoryItem(
                    seller_id=seller_id,
                    content=fact["content"],
                    kind=fact.get("kind", "fact"),
                    source=fact.get("source", "tool_result"),
                    confidence=fact.get("confidence"),
                    metadata={
                        "source_tool": fact.get("source_tool"),
                        "conversation_turn": fact.get("turn_index"),
                    },
                )
                await self.store.upsert(item)
                stored_ids.append(item.id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to store memory item: %s", exc)

        return stored_ids

    # ── Internal: deterministic tool retrieval ──────────────────────

    async def _retrieve_memory(
        self, seller_id: str, user_message: str
    ) -> list[MemoryItem]:
        """Retrieve memory items for a seller query, with timeout protection.

        Uses a short-lived cache keyed by (seller_id, query_hash) to avoid
        repeated lookups for identical queries within a short window.
        """
        cache_key = _hash(f"{seller_id}:{user_message.lower()}")
        now = _now_iso_timestamp()

        # Check cache
        if cache_key in self._recall_cache:
            cached_items, cached_at = self._recall_cache[cache_key]
            if (now - cached_at) < 300:  # 5-minute cache
                return cached_items

        try:
            items = await asyncio.wait_for(
                self.store.recall(
                    seller_id=seller_id,
                    query=user_message,
                    top_k=self.settings.top_k,
                    timeout_ms=self.settings.recall_timeout_ms,
                ),
                timeout=self.settings.recall_timeout_ms / 1000.0,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Memory recall timed out after %dms for seller %s",
                self.settings.recall_timeout_ms,
                seller_id,
            )
            items = []
        except Exception as exc:  # noqa: BLE001
            logger.warning("Memory recall failed: %s", exc)
            items = []

        self._recall_cache[cache_key] = (items, now)
        return items

    # ── Internal: prompt building ───────────────────────────────────

    def _build_system_prompt(
        self,
        seller_profile: dict,
        tool_results: dict[str, Any],
        memory_items: list[MemoryItem],
        channel: str,
    ) -> str:
        """Compose the system prompt from seller profile + tool results + memory."""

        # Seller context block
        seller_lines = [
            f"- display_name: {seller_profile.get('display_name', 'Unknown')}",
            f"- marketplace: {seller_profile.get('marketplace', 'mock-marketplace')}",
            f"- business_category: {seller_profile.get('business_category', 'n/a')}",
            f"- state: {seller_profile.get('state', 'n/a')}",
            f"- city: {seller_profile.get('city', 'n/a')}",
            f"- timezone: {seller_profile.get('timezone', 'Asia/Kolkata')}",
            f"- business_goals: {seller_profile.get('business_goals', 'not specified')}",
            f"- target_growth: {seller_profile.get('target_growth', 'not set')}",
            f"- target_margin: {seller_profile.get('target_margin', 'not set')}",
            f"- available_replenishment_budget: {seller_profile.get('available_replenishment_budget', 0)} paise",
            f"- risk_tolerance: {seller_profile.get('risk_tolerance', 'medium')}",
            f"- preferred_stock_cover_days: {seller_profile.get('preferred_stock_cover_days', 14)}",
            f"- storage_capacity: {seller_profile.get('storage_capacity', 'not set')}",
        ]

        # Memory facts block
        memory_lines: list[str] = []
        if memory_items:
            memory_lines.append("## Recalled Business Memory (from past conversations):")
            for item in memory_items:
                confidence_str = (
                    f" (confidence: {item.confidence})" if item.confidence else ""
                )
                memory_lines.append(
                    f"- [{item.kind}] {item.content}{confidence_str}"
                )
        memory_text = "\n".join(memory_lines) if memory_lines else "None."

        # Tool results block (flattened)
        tool_lines: list[str] = []
        if tool_results:
            for tool_name, result in tool_results.items():
                if isinstance(result, dict) and "error" not in result:
                    # Flatten key metrics for the prompt
                    for key, value in result.items():
                        if isinstance(value, (int, float, str, bool)) and key not in (
                            "seller_id",
                            "data_status",
                            "period_days",
                        ):
                            tool_lines.append(
                                f"- {tool_name}.{key}: {value}"
                            )
        tool_text = "\n".join(tool_lines) if tool_lines else "None."

        voice_guidance = (
            "\n7. For voice responses: keep spoken text concise and natural "
            "(2-3 sentences max), no markdown, no bullet points."
            if channel == "voice"
            else ""
        )

        return f"""You are the Virtual Key Account Manager (Virtual KAM) for the authenticated seller.

SELLER CONTEXT:
{chr(10).join(seller_lines)}

TOOL RESULTS (current business facts - treat as observed/calculated data):
{tool_text}

REMEMBERED BUSINESS MEMORY (from past conversations):
{memory_text}

YOUR ROLE:
You are a commercially thoughtful business partner for this seller.
Investigate before recommending. Prioritize the few actions that matter most.
Explain evidence, assumptions, expected impact, cost, risk, and uncertainty.
Ask one focused question at a time when a missing fact changes the decision.
Never overwhelm the seller with a long list.
Respect the seller's budget ({seller_profile.get('available_replenishment_budget', 0)} paise),
risk tolerance ({seller_profile.get('risk_tolerance', 'medium')}),
and target margin ({seller_profile.get('target_margin', 'not set')}).
Never claim an action was executed without explicit seller approval.
Never invent metrics, competitor prices, dates, stock, or action outcomes.
Distinguish observed / calculated / forecast / scenario / unknown values.
Respond in the same language as the user (default English/Hinglish).
{voice_guidance}

RESPONSE STRUCTURE:
1. What I found — one or two key findings with numbers.
2. Why it matters — quantified business impact where supportable.
3. What I recommend — up to three prioritized actions.
4. Trade-off / risk — budget, margin, uncertainty, operational risk.
5. What I need from you — only if a missing decision blocks the next step."""

    def _build_conversation_history(
        self,
        conversation_history: list[dict[str, str]],
        memory_items: list[MemoryItem],
    ) -> list[dict[str, str]]:
        """Prepend memory findings as system context if not already present.

        Avoids duplicating facts already present in the conversation.
        """
        memory_summary = self._summarize_memory_items(memory_items)
        if not memory_summary:
            return list(conversation_history)

        # Check if memory content is already present in history
        combined_text = " ".join(
            m.get("content", "") for m in conversation_history
        ).lower()
        memory_text_lower = memory_summary.lower()

        # Skip injection if already present
        if memory_text_lower in combined_text:
            return list(conversation_history)

        memory_turn = {
            "role": "system",
            "content": f"[Business memory context]\n{memory_summary}",
        }
        return [memory_turn, *conversation_history]

    def _summarize_memory_items(self, items: list[MemoryItem]) -> str:
        if not items:
            return ""
        lines = []
        for item in items:
            confidence = f" (confidence: {item.confidence})" if item.confidence else ""
            lines.append(f"- [{item.kind}] {item.content}{confidence}")
        return "\n".join(lines)

    def _truncate_and_summarize(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
    ) -> list[dict[str, str]]:
        """Trim conversation to fit token budget.

        Strategy:
        1. Keep system prompt + most recent turns.
        2. If still over budget, summarize oldest turns into a single system block.
        3. Never split tool_call/tool_result pairs (we treat all turns as opaque
           text here; callers should not insert raw tool call blocks into history).
        """
        max_tokens = self.settings.summarize_trigger_tokens
        target_tokens = self.settings.summarize_target_tokens

        # Rough token estimate: ~4 chars per token
        def estimate_tokens(text: str) -> int:
            return len(text) // 4

        total = sum(len(m.get("content", "")) for m in messages) + len(system_prompt)

        if total <= max_tokens:
            return messages

        # Keep system prompt + recent turns
        # Always keep at least the last 2 turns
        kept: list[dict[str, str]] = []
        total_tokens = len(system_prompt) // 4

        for msg in reversed(messages):
            msg_tokens = len(msg.get("content", "")) // 4
            if total_tokens + msg_tokens > max_tokens and len(kept) >= 2:
                break
            kept.insert(0, msg)
            total_tokens += msg_tokens

        # If we still have too many tokens, summarize the dropped turns
        if total_tokens > target_tokens:
            dropped = messages[: len(messages) - len(kept)]
            if dropped:
                summary_text = " | ".join(
                    f"{m.get('role', 'user')}: {m.get('content', '')[:100]}"
                    for m in dropped
                )
                summary_msg = {
                    "role": "system",
                    "content": f"Earlier conversation summary (condensed): {summary_text[:500]}",
                }
                kept.insert(0, summary_msg)

        return kept

    # ── Public capture entry point ──────────────────────────────────

    async def capture_turn(
        self,
        seller_id: str,
        user_message: str,
        assistant_response: str,
        tool_results: dict[str, Any] | None = None,
    ) -> list[str]:
        """Persist durable facts from a completed turn.

        Extracts facts via the extractor, stores them as memory items,
        and returns the list of stored item ids.
        """
        if not self.settings or not self.settings.enabled:
            return []
        if self.settings.capture_mode == "off":
            return []

        try:
            extraction = extract_facts(
                user_message=user_message,
                assistant_response=assistant_response,
                tool_results=tool_results or {},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Fact extraction failed: %s", exc)
            return []

        stored_ids: list[str] = []
        for fact in extraction.facts:
            try:
                item = MemoryItem(
                    seller_id=seller_id,
                    content=fact["content"],
                    kind=fact.get("kind", "fact"),
                    source=fact.get("source", "tool_result"),
                    confidence=fact.get("confidence"),
                    metadata={
                        "source_tool": fact.get("source_tool"),
                        "turn_index": fact.get("turn_index"),
                    },
                )
                await self.store.upsert(item)
                stored_ids.append(item.id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to store memory item: %s", exc)

        return stored_ids


# ── Module-level convenience ──────────────────────────────────────────

_memory_manager: ContextManager | None = None


def get_memory_manager() -> ContextManager:
    """Get or create the singleton agent memory manager."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = ContextManager()
    return _memory_manager


async def build_context_for_agent(
    seller_id: str,
    seller_profile: dict,
    tool_results: dict[str, Any],
    conversation_history: list[dict[str, str]],
    user_message: str,
    channel: str = "text",
) -> dict:
    """Convenience wrapper around AgentContextManager.build_context."""
    manager = get_memory_manager()
    return await manager.build_context(
        seller_id=seller_id,
        seller_profile=seller_profile,
        tool_results=tool_results,
        conversation_history=conversation_history,
        user_message=user_message,
        channel=channel,
    )


async def capture_turn(
    seller_id: str,
    user_message: str,
    assistant_response: str,
    tool_results: dict[str, Any] | None = None,
) -> list[str]:
    """Convenience wrapper around ContextManager.capture_turn."""
    manager = get_memory_manager()
    return await manager.capture_turn(
        seller_id=seller_id,
        user_message=user_message,
        assistant_response=assistant_response,
        tool_results=tool_results,
    )
