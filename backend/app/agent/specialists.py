"""Multi-agent specialist coordinator for the Virtual KAM.

Defines 4 domain specialists plus a Coordinator router:
- Inventory KAM: stockouts, lost demand, supplier lead times, reorder quantities
- Sales KAM: root-cause revenue decomposition (volume/price/availability/cancellations), trends
- Finance KAM: budget constraints, risk/growth profile, margin floor, what-if ROI & outcomes
- Festival KAM: Diwali/wedding/payday seasonality readiness & category demand timing
"""

from __future__ import annotations

import re
from typing import Any, Optional


SPECIALIST_CONFIGS: dict[str, dict[str, Any]] = {
    "sales_kam": {
        "display_name": "Sales KAM",
        "focus": "Root-cause revenue decomposition (Volume, Price, Availability, Cancellations, Segment Mix) and conversion health.",
        "tools": [
            "get_dashboard_kpis",
            "decompose_revenue_change",
            "get_cancellation_breakdown",
            "get_proactive_alerts",
        ],
    },
    "inventory_kam": {
        "display_name": "Inventory KAM",
        "focus": "Stockouts, censored lost units & revenue, 3-vs-14 day supplier lead times, and smart replenishment planning.",
        "tools": [
            "get_inventory_health",
            "calculate_stockout_impact",
            "get_category_seasonality_breakdown",
            "get_smart_replenishment_plan",
            "get_proactive_alerts",
        ],
    },
    "finance_kam": {
        "display_name": "Finance KAM",
        "focus": "Upfront cash vs credit stretch per Seller Decision Profile, margin preservation, What-If ROI, and past outcome track record.",
        "tools": [
            "get_seller_profile",
            "simulate_what_if_scenario",
            "get_outcome_track_record",
            "get_smart_replenishment_plan",
        ],
    },
    "festival_kam": {
        "display_name": "Festival KAM",
        "focus": "Upcoming festival, wedding, and payday demand surges matched against SKU seasonality tags and lead times.",
        "tools": [
            "get_festival_calendar",
            "get_category_seasonality_breakdown",
            "get_proactive_alerts",
            "simulate_what_if_scenario",
        ],
    },
}


def route_query_to_specialists(message: str, allow_default: bool = True) -> list[str]:
    """Deterministically route a seller query to 1+ domain specialists."""
    msg = message.lower()
    selected: list[str] = []

    is_broad = any(
        k in msg
        for k in (
            "why are",
            "sales down",
            "revenue down",
            "summary",
            "summarize",
            "summarise",
            "wrap up",
            "diagnos",
            "what should i do",
            "alert",
            "proactive",
            "priority",
            "attention",
            "overview",
            "store health",
            "how is my store",
            "how are sales",
            "bikri",
        )
    )

    if is_broad or any(
        k in msg
        for k in (
            "sales", "revenue", "order", "cancel", "return", "asp", "price",
            "conversion", "trend", "decompos", "root cause", "visibility",
            "competitor", "listing", "catalog", "category", "categories", "slow", "dead stock",
        )
    ):
        selected.append("sales_kam")

    if is_broad or any(
        k in msg
        for k in (
            "stock", "inventory", "sku", "restock", "replenish", "reorder",
            "lead time", "supplier", "lost sales", "cover", "warehouse", "moq", "saman",
        )
    ):
        selected.append("inventory_kam")

    if is_broad or any(
        k in msg
        for k in (
            "what if", "what-if", "if i spend", "if i delay", "budget", "margin",
            "roi", "profit", "risk", "finance", "outcome", "worked last time",
            "credit", "paisa", "kharch",
        )
    ):
        selected.append("finance_kam")

    if any(
        k in msg
        for k in (
            "festival", "festive", "diwali", "holi", "eid", "christmas", "navratri",
            "rakhi", "pongal", "onam", "wedding", "payday", "season", "event",
            "calendar", "category", "staple", "discretionary",
        )
    ):
        selected.append("festival_kam")

    if not selected and allow_default:
        selected = ["sales_kam", "inventory_kam"]

    # Deduplicate preserving order
    seen: set[str] = set()
    return [s for s in selected if not (s in seen or seen.add(s))]


def collect_tools_for_specialists(specialists: list[str], extra_tools: list[str]) -> list[str]:
    """Merge deterministic tool lists from active specialists + memory/extra triggers."""
    tools: list[str] = []
    for sp in specialists:
        cfg = SPECIALIST_CONFIGS.get(sp)
        if cfg:
            tools.extend(cfg["tools"])
    tools.extend(extra_tools)
    seen: set[str] = set()
    return [t for t in tools if not (t in seen or seen.add(t))]


def parse_what_if_params(message: str, default_budget_inr: float = 15000.0) -> dict[str, Any]:
    """Extract rupee spend, delay days, optional SKU reference, and validation status."""
    msg = message.lower()
    budget = default_budget_inr
    hard_errors: list[str] = []
    notes: list[str] = []

    if re.search(
        r"(?:spend|invest|budget|put|allocate|with)\s*(?:of|around|about)?\s*(?:₹|rs\.?\s*|inr\s*)?-\s*\d+"
        r"|(?:₹|rs\.?\s*|inr\s*)-\s*\d+",
        msg,
    ):
        hard_errors.append("Replenishment budget must be a positive amount greater than ₹0.")
    elif re.search(
        r"(?:spend|invest|budget|put|allocate|with)\s*(?:of|around|about)?\s*(?:₹|rs\.?\s*|inr\s*)?0(?:\.0+)?(?:\s*(?:rupees|rs|inr|k|lakh))?\b",
        msg,
    ):
        hard_errors.append("Replenishment budget cannot be ₹0; please provide a positive budget.")

    if not hard_errors:
        lakh_match = re.search(r"(?:₹|rs\.?\s*|inr\s*)?(\d+(?:\.\d+)?)\s*(?:lakh|lac|l)\b", msg)
        k_match = re.search(r"(?:₹|rs\.?\s*|inr\s*)?(\d+(?:\.\d+)?)\s*k\b", msg)
        num_match = re.search(r"(?:spend|invest|budget|put|allocate|with)\s*(?:of|around|about)?\s*(?:₹|rs\.?\s*|inr\s*)?([\d,]+)", msg)

        if lakh_match:
            budget = float(lakh_match.group(1)) * 100000.0
        elif k_match:
            budget = float(k_match.group(1)) * 1000.0
        elif num_match:
            try:
                parsed = float(num_match.group(1).replace(",", ""))
                if parsed > 0:
                    budget = parsed
            except ValueError:
                pass

    delay_days = 7
    if re.search(r"(?:delay\s+(?:of|by)?|for)\s*-\s*\d+\s*(?:days?|weeks?)", msg):
        hard_errors.append("Delay duration cannot be negative; use 0 or more days.")
    else:
        week_delay = re.search(r"delay[^\d]*(\d+)\s*weeks?", msg)
        day_delay = re.search(r"delay[^\d]*(\d+)\s*days?", msg)
        if week_delay:
            raw_days = int(week_delay.group(1)) * 7
            delay_days = min(60, raw_days)
            if raw_days > 60:
                notes.append("Delay simulation is capped at 60 days.")
        elif day_delay:
            raw_days = int(day_delay.group(1))
            delay_days = min(60, raw_days)
            if raw_days > 60:
                notes.append("Delay simulation is capped at 60 days.")

    sku_match = re.search(r"\b(sku-\d+|SD-[A-Z]+-\d+)\b", message, re.IGNORECASE)
    combined_validation = " ".join([*hard_errors, *notes]) if (hard_errors or notes) else None
    return {
        "budget_inr": budget,
        "delay_days": delay_days,
        "sku_id": sku_match.group(1) if sku_match else None,
        "festival_uplift_pct": 25.0,
        "is_valid": len(hard_errors) == 0,
        "validation_error": combined_validation,
    }


def build_specialist_briefs(
    specialists: list[str],
    tool_results: dict[str, Any],
    seller_context: dict[str, Any],
) -> str:
    """Synthesize structured deterministic memos from consulted specialist findings."""
    lines: list[str] = []

    if "sales_kam" in specialists:
        decomp = tool_results.get("decompose_revenue_change")
        if isinstance(decomp, dict) and decomp.get("summary_text"):
            lines.append(f"[Sales KAM]: {decomp['summary_text']}")

    if "inventory_kam" in specialists:
        oos = tool_results.get("calculate_stockout_impact")
        cat = tool_results.get("get_category_seasonality_breakdown")
        parts: list[str] = []
        if isinstance(oos, dict) and oos.get("summary_text"):
            parts.append(oos["summary_text"])
        if isinstance(cat, dict) and cat.get("long_lead_stockout_skus"):
            long_leads = ", ".join(
                f"{x['title']} ({x['lead_time_days']}d lead)"
                for x in cat["long_lead_stockout_skus"][:3]
            )
            parts.append(f"Long-lead stockouts needing early POs: {long_leads}.")
        if parts:
            lines.append("[Inventory KAM]: " + " ".join(parts))

    if "finance_kam" in specialists:
        whatif = tool_results.get("simulate_what_if_scenario")
        track = tool_results.get("get_outcome_track_record")
        smart = tool_results.get("get_smart_replenishment_plan")
        parts = []
        risk = seller_context.get("risk_tolerance", "medium")
        prio = seller_context.get("growth_vs_margin_priority", "balanced")
        parts.append(f"Decision Profile: risk={risk}, priority={prio}.")
        if isinstance(whatif, dict) and whatif.get("summary_text"):
            parts.append(f"What-If: {whatif['summary_text']} Guidance: {whatif.get('profile_guidance', '')}")
        elif isinstance(smart, dict) and smart.get("recommended_batch"):
            parts.append(
                f"Smart PO Batch: {len(smart['recommended_batch'])} SKUs costing ₹{smart['batch_total_cost_inr']:,.0f} "
                f"for ~₹{smart['batch_expected_revenue_inr']:,.0f} revenue."
            )
        if isinstance(track, dict) and track.get("recent_outcomes"):
            o = track["recent_outcomes"][0]
            parts.append(
                f"Outcome Memory ({track.get('overall_win_rate_pct')}% positive win-rate): "
                f"Last '{o['action_type']}' action ({o['title']}) delivered {o.get('actual_revenue_delta_pct')}% revenue change at {o.get('actual_margin_pct')}% margin."
            )
        lines.append("[Finance KAM]: " + " ".join(parts))

    if "festival_kam" in specialists:
        cal = tool_results.get("get_festival_calendar")
        alerts_res = tool_results.get("get_proactive_alerts")
        parts = []
        if isinstance(cal, dict) and cal.get("events"):
            ev = cal["events"][0]
            parts.append(f"Next event: {ev['event_name']} ({ev['start_date']}).")
        if isinstance(alerts_res, dict) and alerts_res.get("alerts"):
            fest_alerts = [a["message"] for a in alerts_res["alerts"] if a.get("alert_type") == "festival_readiness"]
            if fest_alerts:
                parts.append(fest_alerts[0])
        if parts:
            lines.append("[Festival KAM]: " + " ".join(parts))

    return "\n".join(lines)

