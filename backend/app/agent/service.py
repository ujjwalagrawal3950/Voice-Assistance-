"""KAM agent service.

Orchestrates typed tools to answer seller questions. Uses the Google Gemini
API (while keeping the local Ollama adapter commented below for easy rollback).
Business logic stays in deterministic tools; the LLM never calculates KPIs or
invents data.

The agent follows a deterministic observe→reason→respond loop:
1. Classify the user's intent from keywords to select relevant tools.
2. Call those tools to retrieve current business facts.
3. Feed tool results to the LLM for natural-language explanation.
4. Return a structured response (response_text + spoken_text).

Memory layer:
- Before responding, relevant seller memory is retrieved and injected into
  the system prompt (with a hard timeout to avoid blocking).
- After responding, durable facts are extracted and stored for future turns.
"""

import asyncio
import json
import re
import uuid
from typing import Any, Optional

import httpx

from app.config import settings
from app.agent.guardrails import (
    OFF_TOPIC_REFUSAL,
    build_scope_system_directive,
    classify_query_scope,
    sanitize_assistant_reply,
)
from app.agent.specialists import (
    SPECIALIST_CONFIGS,
    build_specialist_briefs,
    collect_tools_for_specialists,
    parse_what_if_params,
    route_query_to_specialists,
)
from app.agent.tools import TOOL_REGISTRY, TOOL_DESCRIPTIONS, get_seller_profile
from app.agent.tools import TOOL_REGISTRY as BASE_TOOL_REGISTRY
from app.memory.tools import (
    MEMORY_TOOL_REGISTRY,
    MEMORY_TOOL_DESCRIPTIONS,
    get_memory_tools,
    get_memory_tool_descriptions,
)
from app.memory.context_manager import get_memory_manager, build_context_for_agent
from app.memory.store import (
    format_memory_context,
    load_session_history,
    recall_conversation_memories,
    store_conversation_turn,
)


class AgentService:
    """Channel-neutral agent: same logic for text and voice."""

    _GEMINI_TOOL_DECLARATIONS: list[dict[str, Any]] = [
        {
            "name": "search_catalog_skus",
            "description": "Search the seller's active SKU catalog by product name, SKU code, category, or seasonality tag to get sku_id, price, margin, stock, and lead time.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {"type": "STRING", "description": "Product name, keyword, or empty string for top SKUs."},
                    "limit": {"type": "INTEGER", "description": "Max SKUs to return (default 20)."},
                },
            },
        },
        {
            "name": "get_dashboard_kpis",
            "description": "Get overall revenue, orders, units, ASP, cancellation/return/conversion rates, stockouts, and period comparison.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"period_days": {"type": "INTEGER", "description": "Lookback period in days (7, 14, 30, 90)."}},
            },
        },
        {
            "name": "get_sku_performance",
            "description": "Get single SKU performance (30-day revenue, units sold, stock cover days, stockout status). Pass exact sku_id from search_catalog_skus.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"sku_id": {"type": "STRING", "description": "Exact SKU ID such as sku-001 or SD-ELC-001."}},
                "required": ["sku_id"],
            },
        },
        {
            "name": "get_inventory_health",
            "description": "Get full list of out-of-stock SKUs, low cover SKUs, and slow/dead stock candidates.",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "get_sales_trend",
            "description": "Get daily net sales, units, and orders trend over the period.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"period_days": {"type": "INTEGER", "description": "Lookback window in days (default 30)."}},
            },
        },
        {
            "name": "get_cancellation_breakdown",
            "description": "Get cancellations segmented by SKU and cancellation rate vs benchmark.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"period_days": {"type": "INTEGER", "description": "Lookback window in days."}},
            },
        },
        {
            "name": "calculate_stockout_impact",
            "description": "Quantify lost units and lost revenue from stockout-censored demand per SKU.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"period_days": {"type": "INTEGER", "description": "Lookback window in days."}},
            },
        },
        {
            "name": "decompose_revenue_change",
            "description": "Break period revenue change into Volume, Price (ASP), Availability/Stockout, Cancellation, and Mix components.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"period_days": {"type": "INTEGER", "description": "Period window in days."}},
            },
        },
        {
            "name": "calculate_replenishment_plan",
            "description": "Calculate recommended reorder quantity, estimated cost, and budget/margin/storage feasibility for a specific sku_id.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"sku_id": {"type": "STRING", "description": "Exact SKU ID."}},
                "required": ["sku_id"],
            },
        },
        {
            "name": "get_smart_replenishment_plan",
            "description": "Generate prioritized multi-SKU PO replenishment batch aligned with seller budget, supplier lead times, and risk tolerance.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "auto_create_recommendation": {
                        "type": "BOOLEAN",
                        "description": "Set true ONLY when the seller asks to save/create the replenishment recommendation.",
                    }
                },
            },
        },
        {
            "name": "simulate_what_if_scenario",
            "description": "Run a What-If restocking budget vs delay scenario returning expected incremental revenue and margin.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "budget_inr": {"type": "NUMBER", "description": "Planned spend in INR (e.g. 25000)."},
                    "sku_id": {"type": "STRING", "description": "Optional specific SKU ID to focus spend on."},
                    "delay_days": {"type": "INTEGER", "description": "Delay days to quantify lost revenue (default 7)."},
                    "festival_uplift_pct": {"type": "NUMBER", "description": "Festival demand uplift percentage (default 25)."},
                },
            },
        },
        {
            "name": "get_festival_calendar",
            "description": "Get upcoming Indian festival and regional shopping events relevant to the seller.",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "get_category_seasonality_breakdown",
            "description": "Get staple vs discretionary category mix, seasonality sensitivity, and long supplier lead-time stockouts.",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "get_proactive_alerts",
            "description": "Fetch active proactive KAM alerts for imminent stockouts, 3-day cancellation spikes, and festival gaps.",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "get_recommendation_history",
            "description": "List pending, approved, and rejected recommendations with IDs.",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "get_outcome_track_record",
            "description": "Retrieve realized revenue/margin outcomes of past approved recommendations.",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "create_recommendation",
            "description": "Create a draft recommendation card for seller approval on the dashboard. Only call when creating a concrete actionable proposal.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING"},
                    "problem_or_opportunity": {"type": "STRING"},
                    "suggested_action": {"type": "STRING"},
                    "evidence": {"type": "STRING"},
                    "expected_impact": {"type": "STRING"},
                    "cost_or_budget": {"type": "INTEGER", "description": "Cost in paise (INR * 100)."},
                    "risk": {"type": "STRING", "description": "low | medium | high"},
                    "confidence": {"type": "STRING", "description": "low | medium | high"},
                    "urgency": {"type": "STRING", "description": "low | medium | high"},
                },
                "required": ["title", "problem_or_opportunity", "suggested_action"],
            },
        },
        {
            "name": "search_memory",
            "description": "Search seller's durable conversation memory for prior constraints, supplier details, or decisions.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {"type": "STRING"},
                    "top_k": {"type": "INTEGER"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "remember_fact",
            "description": "Store an important business fact, budget change, or supplier constraint shared by the seller.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "content": {"type": "STRING"},
                    "kind": {"type": "STRING", "description": "fact | preference | constraint | goal"},
                },
                "required": ["content"],
            },
        },
    ]

    def __init__(
        self,
        google_api_key: str | None = None,
        google_model: str | None = None,
        google_base_url: str | None = None,
    ):
        # # Local Ollama config (temporarily commented out in favor of Google Gemini API)
        # self.ollama_base_url = (ollama_base_url or settings.ollama_base_url).rstrip("/")
        # self.ollama_model = ollama_model or settings.ollama_model
        self.google_api_key = (
            google_api_key if google_api_key is not None else settings.google_api_key
        ).strip()
        self.google_model = google_model or settings.google_model
        self.google_base_url = (google_base_url or settings.google_base_url).rstrip("/")

        # Merge memory tools into the tool registry
        self._tool_registry = dict(TOOL_REGISTRY)
        self._tool_registry.update(MEMORY_TOOL_REGISTRY)

        self._tool_descriptions = dict(TOOL_DESCRIPTIONS)
        self._tool_descriptions.update(MEMORY_TOOL_DESCRIPTIONS)

        self._memory_manager = None
        self._conversations: dict[str, list[dict[str, str]]] = {}

    # ── Memory manager ──────────────────────────────────────────────

    @property
    def _memory(self):
        if self._memory_manager is None:
            self._memory_manager = get_memory_manager()
        return self._memory_manager

    # ── Intent classification ──────────────────────────────────────────

    def _classify_intent(self, message: str) -> list[str]:
        """Determine which tools are relevant based on message keywords.

        Returns a list of tool names to invoke. This is deterministic and
        does not depend on the LLM formatting tool calls correctly.
        """
        msg = message.lower()
        tools: list[str] = []

        business_keywords = [
            "sales", "revenue", "gmv", "order", "orders", "down", "drop", "dropped",
            "fall", "increase", "decline", "growth", "performance", "business",
            "shop", "store", "dukan", "dukaan", "bikri", "dashboard", "kpi", "metric",
            "pricing", "price", "asp", "margin", "profit", "loss", "visibility",
            "views", "traffic", "conversion", "summary", "summarize", "summarise",
            "wrap up", "next steps", "overview", "store health", "category",
            "categories", "catalog", "catalogue", "competitor", "competitors",
            "planning", "plan", "strategy", "slump", "attention", "dead stock",
            "slow moving",
        ]
        if any(k in msg for k in business_keywords) or re.search(r"(?:₹|\b(?:sku-\d+|SD-[A-Z]+-\d+)\b)", message, re.IGNORECASE):
            tools.append("get_dashboard_kpis")

        # Specific tool triggers
        if any(k in msg for k in ["sku", "product", "item", "stock", "inventory", "out of stock", "oos", "sales", "drop", "decline", "summary", "summarize", "summarise", "slow", "dead stock", "selling"]):
            if "get_sku_performance" not in tools:
                tools.append("get_sku_performance")
            tools.append("get_inventory_health")

        if any(k in msg for k in ["cancel", "cancellation", "return", "refund", "rto", "sales", "drop", "decline", "summary", "summarize", "summarise"]):
            tools.append("get_cancellation_breakdown")

        if any(k in msg for k in ["trend", "trend over time", "daily", "weekly"]):
            tools.append("get_sales_trend")

        if any(k in msg for k in ["festival", "festive", "diwali", "holi", "eid", "christmas", "navratri", "rakhi", "wedding", "payday", "event", "season", "calendar"]):
            tools.append("get_festival_calendar")

        if any(k in msg for k in ["replenish", "restock", "reorder", "order more", "buy stock", "purchase order"]):
            tools.append("calculate_replenishment_plan")

        if any(k in msg for k in ["recommendation", "suggest", "action", "advice", "what should", "improve", "fix", "summary", "summarize", "summarise", "next steps"]):
            tools.append("get_recommendation_history")

        if any(k in msg for k in ["profile", "my account", "my business", "settings", "budget", "margin", "risk"]):
            tools.append("get_seller_profile")

        # Memory tools for past context
        if any(k in msg for k in ["remember", "remembered", "remembered before", "last time",
                                 "previous", "previously", "before", "earlier", "last week",
                                 "previously told", "told me"]):
            tools.append("search_memory")

        if any(k in msg for k in ["remember this", "remember that", "keep in mind",
                                 "remember my", "note that", "make a note", "save this",
                                 "don't forget"]):
            tools.append("remember_fact")

        # Deduplicate while preserving order
        seen = set()
        return [t for t in tools if not (t in seen or seen.add(t))]

    # ── Tool execution ─────────────────────────────────────────────────

    async def _execute_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a registered tool by name with seller-scoped args.

        Supports both sync and async tool functions.
        """
        if tool_name not in self._tool_registry:
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            result = self._tool_registry[tool_name](**args)
            if asyncio.iscoroutine(result):
                result = await result
            return result
        except Exception as e:
            return {"error": str(e)}

    # # ── Ollama calls (temporarily commented out while using Google Gemini API) ──
    #
    # async def _call_ollama(self, messages: list[dict[str, str]]) -> str:
    #     """Call the local Ollama chat API. Returns the assistant's text."""
    #     try:
    #         async with httpx.AsyncClient(timeout=120.0) as client:
    #             resp = await client.post(
    #                 f"{self.ollama_base_url}/api/chat",
    #                 json={
    #                     "model": self.ollama_model,
    #                     "messages": messages,
    #                     "stream": False,
    #                 },
    #             )
    #             resp.raise_for_status()
    #             data = resp.json()
    #             return data.get("message", {}).get("content", "")
    #     except httpx.ConnectError:
    #         raise RuntimeError("Ollama is unreachable. Is it running at "
    #                            f"{self.ollama_base_url}?")
    #     except httpx.HTTPStatusError as e:
    #         raise RuntimeError(f"Ollama returned error: {e.response.status_code}")

    # ── Google Gemini API calls (with native agentic tool calling) ─────

    async def _call_google(
        self,
        messages: list[dict[str, str]],
        *,
        seller_id: str | None = None,
        channel: str = "chat",
        extra_tool_results: dict[str, Any] | None = None,
    ) -> str:
        """Call Google Gemini generateContent with adaptive thinking, tool calling, and fallback."""
        if not self.google_api_key or self.google_api_key.lower().startswith("your-"):
            raise RuntimeError(
                "GOOGLE_API_KEY is not configured. Add your Google AI Studio API key to .env."
            )

        system_parts: list[dict[str, str]] = []
        contents: list[dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role", "user")
            text = (msg.get("content") or "").strip()
            if not text:
                continue
            if role == "system":
                system_parts.append({"text": text})
            else:
                contents.append({
                    "role": "model" if role == "assistant" else "user",
                    "parts": [{"text": text}],
                })

        candidates_order: list[str] = []
        for candidate_model in (
            self.google_model,
            "gemini-3-flash-preview",
            "gemini-flash-lite-latest",
            "gemini-3.5-flash",
            "gemini-flash-latest",
        ):
            m = (candidate_model or "").strip().removeprefix("models/")
            if m and m not in candidates_order:
                candidates_order.append(m)

        headers = {
            "x-goog-api-key": self.google_api_key,
            "Content-Type": "application/json",
        }
        thinking_level = "low" if channel == "voice" else "medium"
        last_error: str | None = None

        async def _post_generate(
            client: httpx.AsyncClient,
            model_name: str,
            turn_contents: list[dict[str, Any]],
            include_thinking: bool = True,
        ) -> httpx.Response:
            gen_cfg: dict[str, Any] = {
                "temperature": 0.25,
                "maxOutputTokens": 2048,
            }
            if include_thinking and "gemini-3" in model_name:
                gen_cfg["thinkingConfig"] = {"thinkingLevel": thinking_level}

            payload: dict[str, Any] = {
                "contents": turn_contents,
                "generationConfig": gen_cfg,
            }
            if system_parts:
                payload["system_instruction"] = {"parts": system_parts}
            if seller_id:
                payload["tools"] = [{"functionDeclarations": self._GEMINI_TOOL_DECLARATIONS}]

            url = f"{self.google_base_url}/models/{model_name}:generateContent"
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 400 and include_thinking and "thinking" in resp.text.lower():
                gen_cfg.pop("thinkingConfig", None)
                resp = await client.post(url, headers=headers, json=payload)
            return resp

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                for model_name in candidates_order:
                    working_contents = list(contents)
                    model_failed_transiently = False

                    for _step in range(5):
                        resp = await _post_generate(client, model_name, working_contents)
                        if resp.status_code == 503:
                            await asyncio.sleep(0.6)
                            resp = await _post_generate(client, model_name, working_contents)

                        if resp.status_code in (404, 503):
                            last_error = f"{model_name} HTTP {resp.status_code}"
                            try:
                                detail = resp.json().get("error", {}).get("message")
                                if detail:
                                    last_error = f"{model_name}: {detail}"
                            except Exception:
                                pass
                            model_failed_transiently = True
                            break

                        resp.raise_for_status()
                        data = resp.json()
                        candidates = data.get("candidates") or []
                        if not candidates:
                            return ""
                        model_content = candidates[0].get("content") or {}
                        parts = model_content.get("parts") or []
                        fn_calls = [p for p in parts if isinstance(p, dict) and "functionCall" in p]
                        if not fn_calls or not seller_id:
                            return "".join(
                                p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p
                            ).strip()

                        # Preserve exact model parts (including thoughtSignature & call id)
                        working_contents.append({"role": "model", "parts": parts})
                        response_parts: list[dict[str, Any]] = []
                        for call_part in fn_calls:
                            fc = call_part["functionCall"]
                            fn_name = str(fc.get("name", ""))
                            fn_args = dict(fc.get("args") or {})
                            fn_args["seller_id"] = seller_id
                            tool_res = await self._execute_tool(fn_name, fn_args)
                            if extra_tool_results is not None:
                                extra_tool_results[fn_name] = tool_res
                            fn_resp_obj: dict[str, Any] = {
                                "name": fn_name,
                                "response": {"result": tool_res},
                            }
                            if fc.get("id"):
                                fn_resp_obj["id"] = fc["id"]
                            response_parts.append({"functionResponse": fn_resp_obj})

                        working_contents.append({"role": "user", "parts": response_parts})

                    if not model_failed_transiently:
                        return ""

                raise RuntimeError(
                    f"Google Gemini API unavailable ({last_error or 'no available model'})"
                )
        except httpx.ConnectError:
            raise RuntimeError(
                f"Google Gemini API is unreachable at {self.google_base_url}."
            )
        except httpx.HTTPStatusError as e:
            detail = f"HTTP {e.response.status_code}"
            try:
                msg = e.response.json().get("error", {}).get("message")
                if msg:
                    detail = f"HTTP {e.response.status_code}: {msg}"
            except Exception:
                pass
            raise RuntimeError(f"Google Gemini API error ({detail})")

    # ── Response helpers ───────────────────────────────────────────────

    def _extract_findings(self, text: str) -> list[str]:
        """Extract key findings from the response."""
        findings = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith(("-", "•", "1.", "2.", "3.", "*")):
                findings.append(line.lstrip("-•1234567890. *").strip())
        return findings[:5]

    @staticmethod
    def _format_indian_rupees(amount_str: str, unit_suffix: str = "") -> str:
        """Convert Indian currency strings like '2,00,000' into natural spoken phrases."""
        sign = ""
        raw = amount_str.strip()
        if raw.startswith("-"):
            sign = "minus "
            raw = raw[1:].strip()
        elif raw.startswith("+"):
            raw = raw[1:].strip()
        numeric_clean = raw.replace(",", "")
        suffix_lower = unit_suffix.strip().lower()
        if suffix_lower in ("l", "lac", "lakh", "lakhs"):
            return f"{sign}{numeric_clean} lakh rupees"
        if suffix_lower in ("cr", "crore", "crores"):
            return f"{sign}{numeric_clean} crore rupees"
        if suffix_lower == "k":
            try:
                val = float(numeric_clean) * 1000
                numeric_clean = str(int(val)) if val.is_integer() else f"{val:.0f}"
            except ValueError:
                return f"{sign}{numeric_clean} thousand rupees"

        if "." in numeric_clean:
            try:
                val = float(numeric_clean)
            except ValueError:
                return f"{sign}{numeric_clean} rupees"
            if val >= 10_000_000:
                return f"{sign}{val / 10_000_000:.2f}".rstrip("0").rstrip(".") + " crore rupees"
            if val >= 100_000:
                return f"{sign}{val / 100_000:.2f}".rstrip("0").rstrip(".") + " lakh rupees"
            return f"{sign}{val:g} rupees"

        try:
            amount = int(numeric_clean)
        except ValueError:
            return f"{sign}{numeric_clean} rupees"

        parts: list[str] = []
        if amount >= 10_000_000:
            crores, amount = divmod(amount, 10_000_000)
            parts.append(f"{crores} crore")
        if amount >= 100_000:
            lakhs, amount = divmod(amount, 100_000)
            parts.append(f"{lakhs} lakh")
        if amount >= 1_000 and (parts or (amount >= 10_000 and amount % 1_000 == 0)):
            thousands, amount = divmod(amount, 1_000)
            parts.append(f"{thousands} thousand")
        if amount > 0 or not parts:
            parts.append(str(amount))
        return f"{sign}{' '.join(parts)} rupees"

    @classmethod
    def _normalize_for_speech(cls, text: str) -> str:
        """Normalize Indian currency, numbers, deltas, and acronyms for natural TTS."""
        normalized = text
        currency_pattern = re.compile(
            r"(?:₹|Rs\.?\s*|INR\s*)([+-]?\s*\d+(?:,\d+)*(?:\.\d+)?)(?:\s*(crores?|cr|lakhs?|lac|l|k)\b)?",
            re.IGNORECASE,
        )
        normalized = currency_pattern.sub(
            lambda m: cls._format_indian_rupees(m.group(1), m.group(2) or ""),
            normalized,
        )
        normalized = normalized.replace("→", " to ").replace("->", " to ")
        normalized = normalized.replace("≥", "at least ").replace("≤", "up to ")
        normalized = normalized.replace("—", ", ").replace("–", ", ")
        normalized = re.sub(r"~(?=\d)", "about ", normalized)
        normalized = re.sub(r"([+-])\s*(\d+(?:\.\d+)?)\s*%", lambda m: ("minus " if m.group(1) == "-" else "") + f"{m.group(2)} percent", normalized)
        normalized = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"\1 percent", normalized)

        acronyms = (
            (r"\bOOS\b", "out of stock"),
            (r"\bASP\b", "average selling price"),
            (r"\bMoM\b", "month over month"),
            (r"\bWoW\b", "week over week"),
            (r"\bYoY\b", "year over year"),
            (r"\bGMV\b", "gross sales"),
            (r"\bSLAs\b", "pickup timelines"),
            (r"\bSLA\b", "pickup timeline"),
            (r"\bSKUs\b(?!-)", "products"),
            (r"\bSKU\b(?!-)", "product"),
            (r"\bSKU-(\d+)\b", r"S K U \1"),
        )
        for pattern, replacement in acronyms:
            normalized = re.sub(pattern, replacement, normalized)

        # Strip leftover emoji / non-ASCII symbols that trip up phoneme engines
        normalized = re.sub(r"[^\x20-\x7E]", " ", normalized)
        normalized = re.sub(r"\s+([,.;!?])", r"\1", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _make_spoken_text(self, full_text: str, channel: str) -> Optional[str]:
        """Produce a concise, TTS-friendly spoken version for voice channel."""
        if channel != "voice":
            return None
        clean = re.sub(r"[*_`#]+", "", full_text)
        clean = re.sub(r"^\s*[-•]\s+", "", clean, flags=re.MULTILINE)
        clean = re.sub(r"(?:^|\n)\s*\d+\.\s+", " ", clean)
        clean = self._normalize_for_speech(clean)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]
        spoken = " ".join(sentences[:5])
        if len(spoken) > 550:
            spoken = " ".join(sentences[:3])
        return spoken or None

    # ── Main entry point ───────────────────────────────────────────────

    async def handle_message(
        self,
        message: str,
        seller_id: str,
        channel: str = "text",
        conversation_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Process a seller message and return a structured agent response.

        This is the shared entry point for both text and voice channels.
        Scope & edge-case guardrails → deterministic tools → LLM explanation.
        """
        conv_id = conversation_id if (conversation_id and conversation_id != "new") else str(uuid.uuid4())
        conv_key = f"{seller_id}:{conv_id}"
        history = self._conversations.get(conv_key, [])
        if not history and conversation_id and conversation_id != "new":
            try:
                history = load_session_history(seller_id, conv_id, limit_turns=10)
            except Exception:
                history = []

        # Step 0: Guardrails & edge-case scope classification before invoking tools/LLM
        scope = classify_query_scope(message, history=history)
        if scope.direct_reply is not None:
            reply_text = scope.direct_reply
            if scope.category in ("greeting", "farewell", "capability"):
                self._conversations[conv_key] = [
                    *history,
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": reply_text},
                ][-20:]
            return {
                "response_text": reply_text,
                "spoken_text": self._make_spoken_text(reply_text, channel),
                "conversation_id": conv_id,
                "findings": self._extract_findings(reply_text),
                "recommendation_ids": [],
                "follow_up_question": None,
                "tool_activity": [],
                "specialists_consulted": [],
                "memory_tool_ids": [],
                "channel": channel,
            }

        seller_context = get_seller_profile(seller_id)

        try:
            recalled_memories = recall_conversation_memories(seller_id, query=message, limit=5)
            memory_context = format_memory_context(recalled_memories)
        except Exception:
            memory_context = "No prior conversation memories recorded yet for this seller."

        needs_scope_check = scope.category == "needs_scope_check"
        scope_directive = build_scope_system_directive(scope)

        # Step 1: Route to specialized KAM agents & collect deterministic tools
        specialists = route_query_to_specialists(message, allow_default=not needs_scope_check)
        extra_tools = [] if needs_scope_check else self._classify_intent(message)
        tool_names = collect_tools_for_specialists(specialists, extra_tools)
        if not tool_names and not needs_scope_check:
            tool_names = ["get_dashboard_kpis"]

        what_if_params = parse_what_if_params(message)

        # Step 2: Call tools deterministically
        tool_results: dict[str, Any] = {}
        for tool_name in tool_names:
            args: dict[str, Any] = {"seller_id": seller_id}

            # Tool-specific argument defaults
            if tool_name in ("get_dashboard_kpis", "get_sales_trend", "get_cancellation_breakdown", "calculate_stockout_impact", "decompose_revenue_change"):
                args["period_days"] = 30
            elif tool_name == "simulate_what_if_scenario":
                if not what_if_params.get("is_valid", True):
                    tool_results["what_if_validation_error"] = {
                        "error": what_if_params.get("validation_error")
                    }
                    continue
                args.update({
                    "budget_inr": what_if_params["budget_inr"],
                    "delay_days": what_if_params["delay_days"],
                    "sku_id": what_if_params["sku_id"],
                    "festival_uplift_pct": what_if_params["festival_uplift_pct"],
                })
                if what_if_params.get("validation_error"):
                    tool_results["what_if_validation_note"] = {
                        "note": what_if_params["validation_error"]
                    }
            elif tool_name == "get_smart_replenishment_plan":
                auto_create = any(k in message.lower() for k in ("create recommendation", "generate recommendation", "save po recommendation"))
                args["auto_create_recommendation"] = auto_create
            elif tool_name == "get_sku_performance":
                sku_match = re.search(r"\b(sku-\d+|SD-[A-Z]+-\d+)\b", message, re.IGNORECASE)
                if sku_match:
                    args["sku_id"] = sku_match.group(1)
                else:
                    continue
            elif tool_name == "calculate_replenishment_plan":
                sku_match = re.search(r"\b(sku-\d+)\b", message, re.IGNORECASE)
                if not sku_match:
                    continue
                args["sku_id"] = sku_match.group(1)
            elif tool_name == "search_memory":
                args["query"] = message
                args["top_k"] = 5
            elif tool_name == "remember_fact":
                args["content"] = message

            result = await self._execute_tool(tool_name, args)
            tool_results[tool_name] = result

        # Preserve rich SKU & alert context for Gemini reasoning
        compact_results = {}
        for tname, tdata in tool_results.items():
            if tname == "get_inventory_health" and isinstance(tdata, dict):
                stockouts_list = tdata.get("stockouts", [])
                compact_results[tname] = {
                    **tdata,
                    "stockout_count": len(stockouts_list),
                    "sample_stockouts": stockouts_list[:18],
                    "stockouts": stockouts_list[:18],
                }
            elif tname == "get_cancellation_breakdown" and isinstance(tdata, dict):
                by_sku = sorted(
                    [x for x in tdata.get("by_sku", []) if x.get("cancellations", 0) > 0],
                    key=lambda x: x.get("cancellations", 0),
                    reverse=True,
                )
                compact_results[tname] = {**tdata, "by_sku": by_sku[:12]}
            elif tname == "calculate_stockout_impact" and isinstance(tdata, dict):
                compact_results[tname] = {
                    **tdata,
                    "top_impacted_skus": tdata.get("top_impacted_skus", [])[:10],
                }
            elif tname == "get_smart_replenishment_plan" and isinstance(tdata, dict):
                compact_results[tname] = {
                    **tdata,
                    "recommended_batch": tdata.get("recommended_batch", [])[:12],
                }
            elif tname == "simulate_what_if_scenario" and isinstance(tdata, dict):
                compact_results[tname] = {
                    **tdata,
                    "sku_allocations": tdata.get("sku_allocations", [])[:10],
                }
            else:
                compact_results[tname] = tdata

        specialist_briefs = (
            build_specialist_briefs(specialists, compact_results, seller_context)
            if specialists
            else "None pre-run (verify query scope first)."
        )
        tool_results_str = json.dumps(compact_results, indent=2, default=str)

        msg_lower = message.lower()
        is_summary_request = any(
            k in msg_lower
            for k in ("summary", "summarize", "summarise", "wrap up", "end call", "next steps")
        )

        if needs_scope_check:
            channel_style = (
                "If IN-SCOPE, respond in 2-4 concise spoken sentences without markdown."
                if channel == "voice"
                else "If IN-SCOPE, answer concisely with verified tool facts and clear numbers."
            )
            system_prompt = f"""
{scope_directive}

================================================================================
SELLER CONTEXT (reference only if the question is genuinely about the store):
{json.dumps(seller_context, indent=2)}
RELEVANT BUSINESS MEMORY:
{memory_context}
================================================================================

NOTE ON UNITS:
Raw database money fields are in paise — divide by 100 for INR (₹); *_inr fields are already in INR.

RULES FOR SCOPE-CHECKED TURNS:
1. If the request is NOT about Snapdeal store operations, products, sales, inventory, pricing, cancellations, marketing/visibility, or business planning, reply ONLY with: "{OFF_TOPIC_REFUSAL}"
2. If it IS a genuine business/product question, call the appropriate tool (`search_catalog_skus`, `get_dashboard_kpis`, etc.) before citing any numbers. Never invent competitor prices, live ad metrics, or non-existent SKU stats.
3. {channel_style}
"""
        else:
            if channel == "voice":
                if is_summary_request:
                    structure_block = (
                        "VOICE CALL WRAP-UP STRUCTURE (keep spoken response to 3-4 clear conversational sentences, no markdown/bullets/bold):\n"
                        "1. Key Issues: briefly restate the main causes with exact observed/calculated figures.\n"
                        "2. Top 2-3 Recommendations: restate the prioritized actions and expected impact range.\n"
                        "3. Next Step: invite the seller to approve the actions in the Recommendations tab."
                    )
                elif len(history) == 0:
                    structure_block = (
                        "VOICE CALL OPENING TURN (keep spoken response to 2-4 natural conversational sentences, NO markdown/bullets/bold):\n"
                        "1. State key findings comparing last month vs this month with exact metrics and root-cause drivers (stockout loss vs cancellations vs ASP).\n"
                        "2. Explicitly distinguish Observed vs Calculated vs Estimated values.\n"
                        "3. Ask ONE focused diagnostic follow-up question to confirm the next step."
                    )
                else:
                    structure_block = (
                        "VOICE FOLLOW-UP TURN (keep spoken response to 2-4 natural conversational sentences, NO markdown/bullets/bold):\n"
                        "1. Respond directly to what the seller just shared, referencing prior memory/outcomes when relevant.\n"
                        "2. Recommend 2-3 practical prioritized actions within their budget, risk tolerance, and margin floor.\n"
                        "3. State key trade-offs/assumptions and ask ONE focused next-step question."
                    )
            else:
                structure_block = (
                    "RESPONSE STRUCTURE (follow these numbered sections ONLY for in-scope store analysis/planning replies; NEVER wrap a refusal into these sections):\n"
                    "1. WHAT I FOUND — 1-2 key findings comparing periods with exact metrics, affected SKUs, and Observed/Calculated labels.\n"
                    "2. WHY IT MATTERS — quantified business impact (root-cause Volume/Price/Availability split, stockout lost units & revenue).\n"
                    "3. WHAT I RECOMMEND — up to 3 prioritized actions, each specifying Action, Evidence, Expected impact (range), Cost/budget, Risk, Confidence, Assumptions.\n"
                    "4. TRADE-OFF / RISK — budget fit, margin constraints, supplier lead times (3 vs 14 days), and operational risks.\n"
                    "5. WHAT I NEED FROM YOU — ONLY if a decision is needed to proceed; ask ONE focused question."
                )

            market_context = {
                "festival_calendar": compact_results.get("get_festival_calendar"),
                "category_and_lead_times": compact_results.get("get_category_seasonality_breakdown"),
                "notes": [
                    "Indian festival surges (Diwali, wedding season, payday spikes) are scenario-only unless backed by observed history.",
                    "Factor supplier lead times (3-14 days) into replenishment timing.",
                ],
            }

            system_prompt = f"""
{scope_directive}

You are the Virtual Key Account Manager (Virtual KAM) for an Indian marketplace seller.
You are not a generic chatbot. You are a commercially thoughtful business partner who understands the seller's shop, remembers relevant business context, notices important changes, investigates causes, identifies opportunities, explains trade-offs, and helps the seller decide what to do next.
Active Specialist Coordinator Team: {', '.join(SPECIALIST_CONFIGS[s]['display_name'] for s in specialists)}

================================================================================
SELLER CONTEXT (provided dynamically):
{json.dumps(seller_context, indent=2)}
================================================================================

RELEVANT BUSINESS MEMORY (from past conversations):
{memory_context}

MARKET & SEASONALITY CONTEXT:
{json.dumps(market_context, indent=2, default=str)}

SPECIALIST BRIEFS (deterministic domain findings):
{specialist_briefs}

TOOL RESULTS (current business facts — treat as observed/calculated data):
{tool_results_str}

NOTE ON UNITS:
In this_month / last_month and *_inr intelligence summaries, amounts are already in INR (₹). Raw database fields (revenue, average_selling_price, available_replenishment_budget) are in integer paise — divide by 100 for INR (₹).

RULES (NON-NEGOTIABLE):
1. ALWAYS rely on tool results, specialist briefs, and conversation memory before answering. Never invent metrics, competitor prices, dates, stock quantities, or action outcomes.
2. If the seller mentions any specific product name, SKU, custom What-If budget/delay, or question not covered in TOOL RESULTS, call the appropriate function tool (`search_catalog_skus`, `get_sku_performance`, `simulate_what_if_scenario`, `get_sales_trend`, `search_memory`, etc.) instead of guessing or saying data is unavailable.
3. If `search_catalog_skus` finds 0 matches, or competitor prices / external ad bids / tax-legal rulings / live fulfillment tracking are requested, state clearly what is NOT in your data (Unknown) — never invent prices or stock.
4. If `what_if_validation_error` is present in TOOL RESULTS (e.g., negative or zero budget/delay), explain the constraint clearly and ask for a valid positive number instead of inventing a simulation.
5. Never calculate KPIs yourself in your head — cite exact tool figures and distinguish Observed / Calculated / Forecast / Scenario / Unknown values clearly.
6. Respect the seller's ₹{seller_context.get('available_replenishment_budget', 4000000) / 100:,.0f} replenishment budget, risk tolerance ({seller_context.get('risk_tolerance', 'medium')}), growth/margin priority ({seller_context.get('growth_vs_margin_priority', 'balanced')}), and target margin ({seller_context.get('target_margin', 0.25)}).
7. High-impact actions (purchasing, budget commitments, payment transfers, stock updates, live price changes) require explicit seller approval. Prepare draft recommendations (`create_recommendation`), never claim execution.
8. Reference past conversation memories and prior recommendation outcomes when relevant; do not repeat previously rejected recommendations unless the situation changed.
9. Ask ONE focused question at a time. Respond in natural English or Hinglish as appropriate.

{structure_block}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": message},
        ]

        # Step 4: Get LLM response (with live Gemini function calling + automatic model fallback)
        # final_reply = await self._call_ollama(messages)
        extra_tool_results: dict[str, Any] = {}
        final_reply = await self._call_google(
            messages,
            seller_id=seller_id,
            channel=channel,
            extra_tool_results=extra_tool_results,
        )
        if extra_tool_results:
            tool_results.update(extra_tool_results)
            compact_results.update(extra_tool_results)

        # Post-LLM safety guard: neutralize leaked programming code blocks or empty outputs
        final_reply, _ = sanitize_assistant_reply(final_reply, scope)
        is_refusal_reply = final_reply.startswith("I can't help with that.")

        # Persist conversation turns in memory (skip polluting durable business memory on off-topic refusals)
        turn_num = (len(history) // 2) + 1
        if not is_refusal_reply:
            self._conversations[conv_key] = [
                *history,
                {"role": "user", "content": message},
                {"role": "assistant", "content": final_reply},
            ][-20:]
            try:
                store_conversation_turn(
                    seller_id=seller_id,
                    conversation_id=conv_id,
                    turn_number=turn_num,
                    user_message=message,
                    assistant_response=final_reply,
                    tool_results=compact_results,
                )
            except Exception:
                # Never break user chat flow if optional SQLite persistence fails
                pass

        # Step 5: Build structured response
        spoken_text = self._make_spoken_text(final_reply, channel)

        # Capture any recommendation IDs created during tool execution
        recommendation_ids: list[str] = []
        for name, result in tool_results.items():
            if name == "create_recommendation" and isinstance(result, dict):
                rid = result.get("id")
                if rid:
                    recommendation_ids.append(rid)
            elif name == "get_smart_replenishment_plan" and isinstance(result, dict):
                rid = result.get("created_recommendation_id")
                if rid:
                    recommendation_ids.append(rid)

        # Capture any memory tool results
        memory_tool_ids: list[str] = []
        for name, result in tool_results.items():
            if name == "remember_fact" and isinstance(result, dict):
                rid = result.get("id")
                if rid:
                    memory_tool_ids.append(rid)

        return {
            "response_text": final_reply,
            "spoken_text": spoken_text,
            "conversation_id": conv_id,
            "findings": self._extract_findings(final_reply),
            "recommendation_ids": recommendation_ids,
            "follow_up_question": None,
            "tool_activity": list(tool_results.keys()),
            "specialists_consulted": [SPECIALIST_CONFIGS[s]["display_name"] for s in specialists],
            "memory_tool_ids": memory_tool_ids,
            "channel": channel,
        }


from typing import Optional  # noqa: E402

agent_service = AgentService()
