"""Deterministic fact extraction for Virtual KAM memory.

Extracts durable, seller-relevant facts from assistant responses and tool
results so they can be persisted as memory items.

Extraction is deterministic: same input always produces same facts.
No random sampling, no timestamps in extracted content.
"""

from __future__ import annotations

import re
from typing import Any


class FactExtractionError(Exception):
    """Raised when fact extraction fails unexpectedly."""


def extract_facts(
    user_message: str,
    assistant_response: str,
    tool_results: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Extract durable facts from a completed conversation turn.

    Returns a list of dicts with keys:
        - content: str (the fact text)
        - kind: str ("fact", "preference", "opportunity", "issue", "goal")
        - confidence: float | None
        - source_tool: str | None
        - turn_index: int | None

    Heuristics (deterministic, no LLM required):
    - SKU stockout mentions from tool results
    - Budget/margin constraints from seller profile/tool results
    - Explicit seller statements of preference or goal
    - Numerical targets mentioned by the user
    """

    facts: list[dict[str, str]] = []

    # 1. Extract from tool results
    tool_results = tool_results or {}
    facts.extend(_extract_from_tool_results(tool_results))

    # 2. Extract from seller's explicit statements
    facts.extend(_extract_from_user_message(user_message))

    # 3. Extract from assistant commitments
    facts.extend(_extract_from_assistant_response(assistant_response))

    return facts


def _extract_from_tool_results(tool_results: dict[str, Any]) -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []

    for tool_name, result in tool_results.items():
        if not isinstance(result, dict) or "error" in result:
            continue

        # Dashboard KPIs
        if tool_name == "get_dashboard_kpis":
            revenue = result.get("revenue")
            if revenue is not None:
                facts.append({
                    "content": f"Current gross sales: {revenue} paise",
                    "kind": "fact",
                    "source_tool": "get_dashboard_kpis",
                    "confidence": 1.0,
                })
            cancellation = result.get("cancellation_rate")
            if cancellation is not None:
                facts.append({
                    "content": f"Current cancellation rate: {cancellation * 100:.1f}%",
                    "kind": "fact",
                    "source_tool": "get_dashboard_kpis",
                    "confidence": 1.0,
                })
            stockouts = result.get("stockout_sku_count")
            if stockouts is not None and stockouts > 0:
                facts.append({
                    "content": f"{stockouts} product(s) currently out of stock",
                    "kind": "fact",
                    "source_tool": "get_dashboard_kpis",
                    "confidence": 1.0,
                })

        # Inventory health
        if tool_name == "get_inventory_health":
            stockouts = result.get("stockouts", [])
            for sku in stockouts[:5]:
                sku_code = sku.get("sku_code", "unknown")
                title = sku.get("title", "unknown product")
                facts.append({
                    "content": f"{title} ({sku_code}) is out of stock",
                    "kind": "stockout",
                    "source_tool": "get_inventory_health",
                    "confidence": 1.0,
                })
            low_cover = result.get("low_cover", [])
            for sku in low_cover[:3]:
                sku_code = sku.get("sku_code", "unknown")
                cover = sku.get("cover_days")
                facts.append({
                    "content": f"{sku_code} has only {cover} days of stock cover",
                    "kind": "low_stock",
                    "source_tool": "get_inventory_health",
                    "confidence": 1.0,
                })

        # Forecast / replenishment
        if tool_name == "calculate_replenishment_plan":
            reorder_qty = result.get("recommended_reorder_quantity", 0)
            if reorder_qty and reorder_qty > 0:
                sku_code = result.get("sku_code", "unknown")
                title = result.get("title", "unknown")
                facts.append({
                    "content": f"Recommended reorder for {title} ({sku_code}): {reorder_qty} units",
                    "kind": "replenishment",
                    "source_tool": "calculate_replenishment_plan",
                    "confidence": 0.9,
                })

    return facts


def _extract_from_user_message(message: str) -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []
    msg = message.lower()

    # Budget mentions
    budget_match = re.search(r"(?:budget|budget of|budget is|budget of ₹?)\s*₹?(\d[\d,]*)", msg)
    if budget_match:
        facts.append({
            "content": f"Seller budget: ₹{budget_match.group(1)}",
            "kind": "budget",
            "confidence": 0.9,
        })

    # Margin mentions
    margin_match = re.search(r"(?:margin|margin of|margin is)\s*(\d+(?:\.\d+)?)%?", msg)
    if margin_match:
        facts.append({
            "content": f"Target margin: {margin_match.group(1)}%",
            "kind": "margin",
            "confidence": 0.9,
        })

    # Stock cover mentions
    cover_match = re.search(r"(?:stock cover|cover days)\s*(?:of|is)?\s*(\d+)", msg)
    if cover_match:
        facts.append({
            "content": f"Preferred stock cover: {cover_match.group(1)} days",
            "kind": "preference",
            "confidence": 0.9,
        })

    # Explicit goals
    goal_keywords = ["goal", "target", "want to", "need to", "want to grow", "want to reach"]
    for kw in goal_keywords:
        if kw in msg:
            # Extract a reasonable window around the keyword
            idx = msg.find(kw)
            snippet = msg[max(0, idx - 10):idx + 60].strip()
            facts.append({
                "content": f"Seller goal/context: ...{snippet}...",
                "kind": "goal",
                "confidence": 0.7,
            })
            break  # Only one goal per message to avoid noise

    return facts


def _extract_from_assistant_response(response: str) -> list[dict[str, str]]:
    facts: list[dict[str, str]] = []

    # If the assistant committed to a specific action or number, capture it
    action_match = re.search(r"(?:recommend|recommend|should|should you)\s+(.{0,80})", response, re.IGNORECASE)
    if action_match:
        snippet = action_match.group(1).strip()
        facts.append({
            "content": f"Assistant recommended: {snippet}",
            "kind": "recommendation",
            "confidence": 0.7,
        })

    return facts


def extract_facts_from_turn(
    user_message: str,
    assistant_response: str,
    tool_results: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract structured conversation memory fields for SQLite persistence.

    Returns dict with problem_summary, solution_summary, key_takeaway,
    related_sku_ids (comma-separated SKU codes), facts list, and confidence.
    """
    tool_results = tool_results or {}
    facts = extract_facts(user_message, assistant_response, tool_results)

    problem_parts: list[str] = []
    solution_parts: list[str] = []
    takeaway_parts: list[str] = []
    sku_codes: list[str] = []

    def _add_sku(code: str | None) -> None:
        if code and code not in sku_codes:
            sku_codes.append(code)

    # Extract explicit SKU references from text
    for m in re.findall(r"\b(SD-[A-Z]+-\d+|sku-\d+)\b", f"{user_message} {assistant_response}", re.IGNORECASE):
        _add_sku(m.upper() if m.upper().startswith("SD-") else m.lower())

    decomp = tool_results.get("decompose_revenue_change")
    if isinstance(decomp, dict) and decomp.get("summary_text"):
        problem_parts.append(decomp["summary_text"])

    oos_impact = tool_results.get("calculate_stockout_impact")
    if isinstance(oos_impact, dict) and oos_impact.get("affected_sku_count", 0) > 0:
        for item in oos_impact.get("top_impacted_skus", [])[:5]:
            _add_sku(item.get("sku_code") or item.get("sku_id"))
        if not problem_parts and oos_impact.get("summary_text"):
            problem_parts.append(oos_impact["summary_text"])

    smart = tool_results.get("get_smart_replenishment_plan")
    if isinstance(smart, dict) and smart.get("recommended_batch"):
        batch = smart["recommended_batch"]
        for item in batch[:5]:
            _add_sku(item.get("sku_code") or item.get("sku_id"))
        titles = ", ".join(f"{x['title']} ({x['recommended_qty']}u)" for x in batch[:3])
        solution_parts.append(
            f"Recommended PO for {titles} (total ₹{smart.get('batch_total_cost_inr', 0):,.0f})"
        )

    whatif = tool_results.get("simulate_what_if_scenario")
    if isinstance(whatif, dict) and whatif.get("summary_text"):
        for item in whatif.get("sku_allocations", [])[:5]:
            _add_sku(item.get("sku_code") or item.get("sku_id"))
        solution_parts.append(whatif["summary_text"])

    kpis = tool_results.get("get_dashboard_kpis")
    if isinstance(kpis, dict) and not problem_parts:
        this_m = kpis.get("this_month") or {}
        last_m = kpis.get("last_month") or {}
        if this_m and last_m:
            problem_parts.append(
                f"Sales ₹{last_m.get('sales_inr', 0):,.0f} → ₹{this_m.get('sales_inr', 0):,.0f}; "
                f"Stockouts {this_m.get('out_of_stock_skus', 0)}; Cancel {this_m.get('cancellation_rate_pct', 0)}%"
            )

    if not solution_parts:
        rec_facts = [f["content"] for f in facts if f.get("kind") in ("recommendation", "replenishment")]
        if rec_facts:
            solution_parts.append("; ".join(rec_facts[:2]))
        else:
            first_sent = re.split(r"(?<=[.!?])\s+", assistant_response.strip())[0] if assistant_response else ""
            if first_sent:
                solution_parts.append(first_sent[:220])

    # Key takeaway highlights constraints/outcomes/user goals
    pref_facts = [f["content"] for f in facts if f.get("kind") in ("budget", "margin", "preference", "goal")]
    if pref_facts:
        takeaway_parts.extend(pref_facts[:2])
    elif oos_impact and isinstance(oos_impact, dict) and oos_impact.get("total_lost_revenue_inr"):
        takeaway_parts.append(
            f"Censored stockout loss estimated at ₹{oos_impact['total_lost_revenue_inr']:,.0f} across {oos_impact.get('affected_sku_count', 0)} SKUs"
        )
    elif facts:
        takeaway_parts.append(facts[0]["content"])

    return {
        "problem_summary": " | ".join(problem_parts)[:500] if problem_parts else f"Seller asked: {user_message[:180]}",
        "solution_summary": " | ".join(solution_parts)[:500] if solution_parts else "Provided data-backed KAM guidance.",
        "key_takeaway": " | ".join(takeaway_parts)[:400] if takeaway_parts else user_message[:200],
        "related_sku_ids": ", ".join(sku_codes[:10]),
        "facts": facts,
        "confidence": 0.9 if tool_results else 0.7,
    }
