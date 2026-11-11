"""Commerce intelligence, root-cause diagnosis, stockout impact, what-if planning,
seller profile alignment, outcome memory weighting, and proactive alert engine.

All computations are 100% deterministic from SQLite seller, product,
daily_performance, calendar_event, and recommendation records.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import (
    CalendarEvent,
    DailyPerformance,
    ProactiveAlert,
    Product,
    Recommendation,
    Seller,
)
from app.services.kpi import (
    calculate_average_selling_price,
    calculate_cancellation_rate,
    calculate_gross_sales,
    calculate_orders,
    calculate_units_sold,
)


def _inr(paise: float | int) -> float:
    return round(float(paise) / 100.0, 2)


def _sku_margin_fraction(product: Product) -> float:
    if product.selling_price <= 0:
        return 0.0
    return (product.selling_price - product.unit_cost) / product.selling_price


def calculate_stockout_impact(
    db: Session,
    seller_id: str,
    period_days: int = 30,
    as_of: Optional[date] = None,
) -> dict[str, Any]:
    """Quantify censored demand (lost units & lost revenue) due to stockouts."""
    end_date = as_of or date.today()
    curr_start = end_date - timedelta(days=period_days - 1)
    lookback_start = end_date - timedelta(days=max(period_days * 2, 60) - 1)

    products = (
        db.query(Product)
        .filter(Product.seller_id == seller_id, Product.active == True)  # noqa: E712
        .all()
    )
    perf_rows = (
        db.query(DailyPerformance)
        .filter(
            DailyPerformance.seller_id == seller_id,
            DailyPerformance.perf_date >= lookback_start,
            DailyPerformance.perf_date <= end_date,
        )
        .all()
    )

    by_sku: dict[str, list[DailyPerformance]] = {}
    for row in perf_rows:
        by_sku.setdefault(row.sku_id, []).append(row)

    items: list[dict[str, Any]] = []
    total_lost_units = 0
    total_lost_rev_paise = 0
    total_lost_margin_paise = 0

    for prod in products:
        sku_rows = by_sku.get(prod.id, [])
        curr_rows = [r for r in sku_rows if r.perf_date >= curr_start]
        prev_rows = [r for r in sku_rows if r.perf_date < curr_start]

        stockout_days = sum(1 for r in curr_rows if r.stockout_indicator)
        if stockout_days == 0 and prod.current_stock <= 0:
            # Fallback if stocked out but daily rows omitted indicator
            stockout_days = sum(1 for r in curr_rows if r.units_sold == 0)
        if stockout_days == 0:
            continue

        curr_active = [r.units_sold for r in curr_rows if not r.stockout_indicator and r.units_sold > 0]
        prev_active = [r.units_sold for r in prev_rows if not r.stockout_indicator and r.units_sold > 0]

        if len(curr_active) >= 5:
            velocity = sum(curr_active) / len(curr_active)
            velocity_source = f"current_{len(curr_active)}d_in_stock"
        elif prev_active:
            # Spread over prior non-stockout days (or full prior window if few gaps)
            denom = max(len(prev_active), min(len(prev_rows), period_days) if sum(1 for r in prev_rows if r.stockout_indicator) == 0 else len(prev_active))
            velocity = sum(prev_active) / max(1, denom)
            velocity_source = "prior_period_baseline"
        else:
            continue

        if velocity <= 0:
            continue

        lost_units = int(round(velocity * stockout_days))
        if lost_units <= 0:
            continue
        lost_rev = lost_units * prod.selling_price
        lost_margin = lost_units * max(0, prod.selling_price - prod.unit_cost)

        total_lost_units += lost_units
        total_lost_rev_paise += lost_rev
        total_lost_margin_paise += lost_margin

        items.append({
            "sku_id": prod.id,
            "sku_code": prod.sku_code,
            "title": prod.title,
            "category": prod.category,
            "demand_segment": prod.demand_segment,
            "seasonality_tag": prod.seasonality_tag or "evergreen",
            "supplier_lead_time_days": prod.supplier_lead_time_days,
            "current_stock": prod.current_stock,
            "stockout_days": stockout_days,
            "avg_daily_velocity": round(velocity, 2),
            "velocity_source": velocity_source,
            "lost_units": lost_units,
            "lost_revenue_inr": _inr(lost_rev),
            "lost_margin_inr": _inr(lost_margin),
        })

    items.sort(key=lambda x: x["lost_revenue_inr"], reverse=True)
    top_names = ", ".join(
        f"{x['title']} (~{x['lost_units']} units ≈ ₹{x['lost_revenue_inr']:,.0f})"
        for x in items[:3]
    )
    summary = (
        f"Estimated {total_lost_units} lost units (~₹{_inr(total_lost_rev_paise):,.0f} revenue) "
        f"across {len(items)} stockout-affected SKUs. Top impact: {top_names}."
        if items
        else "No measurable revenue loss from stockouts in the current window."
    )

    return {
        "seller_id": seller_id,
        "period_days": period_days,
        "affected_sku_count": len(items),
        "total_lost_units": total_lost_units,
        "total_lost_revenue_paise": total_lost_rev_paise,
        "total_lost_revenue_inr": _inr(total_lost_rev_paise),
        "total_lost_margin_inr": _inr(total_lost_margin_paise),
        "top_impacted_skus": items[:10],
        "summary_text": summary,
        "data_status": "estimated",
    }


def decompose_revenue_change(
    db: Session,
    seller_id: str,
    period_days: int = 30,
    as_of: Optional[date] = None,
) -> dict[str, Any]:
    """Mathematical root-cause decomposition: Volume, Price, Availability, Cancellation, Mix."""
    period_end = as_of or date.today()
    comparison_end = period_end - timedelta(days=period_days)

    curr_rev_k = calculate_gross_sales(db, seller_id, period_end, period_days)
    prev_rev_k = calculate_gross_sales(db, seller_id, comparison_end, period_days)
    curr_units_k = calculate_units_sold(db, seller_id, period_end, period_days)
    prev_units_k = calculate_units_sold(db, seller_id, comparison_end, period_days)
    curr_orders_k = calculate_orders(db, seller_id, period_end, period_days)
    prev_orders_k = calculate_orders(db, seller_id, comparison_end, period_days)
    curr_asp_k = calculate_average_selling_price(db, seller_id, period_end, period_days)
    prev_asp_k = calculate_average_selling_price(db, seller_id, comparison_end, period_days)
    curr_cancel_k = calculate_cancellation_rate(db, seller_id, period_end, period_days)
    prev_cancel_k = calculate_cancellation_rate(db, seller_id, comparison_end, period_days)

    rev_new = curr_rev_k["value"]
    rev_old = prev_rev_k["value"]
    units_new = curr_units_k["value"]
    units_old = prev_units_k["value"]
    asp_new = (rev_new / units_new) if units_new > 0 else float(curr_asp_k["value"] or 0)
    asp_old = (rev_old / units_old) if units_old > 0 else float(prev_asp_k["value"] or 0)

    delta_rev = rev_new - rev_old
    volume_effect = (units_new - units_old) * asp_old
    price_effect = units_old * (asp_new - asp_old)
    interaction_effect = (units_new - units_old) * (asp_new - asp_old)

    # Operational attribution: availability (incremental stockout loss) & cancellations
    curr_stockout_impact = calculate_stockout_impact(db, seller_id, period_days=period_days, as_of=period_end)
    prev_stockout_impact = calculate_stockout_impact(db, seller_id, period_days=period_days, as_of=comparison_end)
    incremental_oos_loss_inr = max(
        0.0,
        curr_stockout_impact["total_lost_revenue_inr"] - prev_stockout_impact["total_lost_revenue_inr"],
    )

    c_rate_new = curr_cancel_k["value"] or 0.0
    c_rate_old = prev_cancel_k["value"] or 0.0
    excess_cancel_orders = max(0.0, (c_rate_new - c_rate_old) * (curr_orders_k["value"] or 0))
    cancellation_drag_inr = round(excess_cancel_orders * _inr(asp_new if asp_new > 0 else asp_old), 2)

    # Category / Mix effect (staples vs discretionary shift)
    curr_start = period_end - timedelta(days=period_days - 1)
    comp_start = comparison_end - timedelta(days=period_days - 1)
    products = {
        p.id: p
        for p in db.query(Product).filter(Product.seller_id == seller_id).all()
    }
    rows = (
        db.query(DailyPerformance)
        .filter(
            DailyPerformance.seller_id == seller_id,
            DailyPerformance.perf_date >= comp_start,
            DailyPerformance.perf_date <= period_end,
        )
        .all()
    )
    seg_stats = {
        "staple": {"prev_inr": 0.0, "curr_inr": 0.0},
        "discretionary": {"prev_inr": 0.0, "curr_inr": 0.0},
    }
    for r in rows:
        p = products.get(r.sku_id)
        seg = p.demand_segment if p and p.demand_segment in seg_stats else "discretionary"
        bucket = "curr_inr" if r.perf_date >= curr_start else "prev_inr"
        seg_stats[seg][bucket] += _inr(r.gross_sales)

    abs_delta_inr = abs(_inr(delta_rev)) or 1.0
    volume_share_pct = round(abs(_inr(volume_effect)) / abs_delta_inr * 100, 1) if delta_rev != 0 else 0.0
    price_share_pct = round(abs(_inr(price_effect)) / abs_delta_inr * 100, 1) if delta_rev != 0 else 0.0

    # Breakdown of negative revenue pressure when revenue declined
    if delta_rev < 0:
        avail_inr = min(abs(_inr(delta_rev)), incremental_oos_loss_inr or curr_stockout_impact["total_lost_revenue_inr"])
        cancel_inr = min(max(0.0, abs(_inr(delta_rev)) - avail_inr), cancellation_drag_inr)
        remaining_mix_inr = max(0.0, abs(_inr(delta_rev)) - avail_inr - cancel_inr)
        availability_pct = round(avail_inr / abs_delta_inr * 100, 1)
        cancellation_pct = round(cancel_inr / abs_delta_inr * 100, 1)
        mix_demand_pct = round(remaining_mix_inr / abs_delta_inr * 100, 1)
    else:
        avail_inr = 0.0
        cancel_inr = 0.0
        remaining_mix_inr = 0.0
        availability_pct = 0.0
        cancellation_pct = 0.0
        mix_demand_pct = 0.0

    direction = "down" if delta_rev < 0 else ("up" if delta_rev > 0 else "flat")
    summary_text = (
        f"Revenue is {direction} ₹{abs(_inr(delta_rev)):,.0f} ({abs(_inr(delta_rev)) / max(1.0, _inr(rev_old)) * 100:.1f}%): "
        f"volume effect accounts for {volume_share_pct:.0f}% (₹{_inr(volume_effect):+,.0f}), "
        f"price effect is {price_share_pct:.0f}% (ASP ₹{_inr(asp_old):,.0f} → ₹{_inr(asp_new):,.0f})."
    )
    if delta_rev < 0:
        summary_text += (
            f" Driver split: ~{availability_pct:.0f}% stockout availability loss (₹{avail_inr:,.0f}), "
            f"~{cancellation_pct:.0f}% excess cancellations (₹{cancel_inr:,.0f}), "
            f"~{mix_demand_pct:.0f}% organic/visibility mix shift (₹{remaining_mix_inr:,.0f})."
        )

    return {
        "seller_id": seller_id,
        "period_days": period_days,
        "previous_revenue_inr": _inr(rev_old),
        "current_revenue_inr": _inr(rev_new),
        "revenue_change_inr": _inr(delta_rev),
        "previous_units": units_old,
        "current_units": units_new,
        "previous_asp_inr": round(_inr(asp_old), 2),
        "current_asp_inr": round(_inr(asp_new), 2),
        "components": {
            "volume_effect_inr": round(_inr(volume_effect), 2),
            "price_effect_inr": round(_inr(price_effect), 2),
            "interaction_effect_inr": round(_inr(interaction_effect), 2),
            "volume_share_pct": volume_share_pct,
            "price_share_pct": price_share_pct,
        },
        "drivers": {
            "availability_stockout_loss_inr": round(avail_inr, 2),
            "availability_share_pct": availability_pct,
            "cancellation_drag_inr": round(cancel_inr, 2),
            "cancellation_share_pct": cancellation_pct,
            "mix_and_visibility_inr": round(remaining_mix_inr, 2),
            "mix_and_visibility_share_pct": mix_demand_pct,
        },
        "segment_performance": {
            k: {
                "previous_inr": round(v["prev_inr"], 2),
                "current_inr": round(v["curr_inr"], 2),
                "change_inr": round(v["curr_inr"] - v["prev_inr"], 2),
            }
            for k, v in seg_stats.items()
        },
        "summary_text": summary_text,
        "data_status": "calculated",
    }


def get_outcome_track_record(db: Session, seller_id: str) -> dict[str, Any]:
    """Aggregate Recommendation outcome memory to weight confidence of future suggestions."""
    rows = (
        db.query(Recommendation)
        .filter(Recommendation.seller_id == seller_id)
        .order_by(Recommendation.updated_at.desc())
        .all()
    )
    measured = [r for r in rows if r.outcome_status in ("positive", "neutral", "negative")]
    by_type: dict[str, dict[str, Any]] = {}

    for r in measured:
        atype = r.action_type or "general"
        entry = by_type.setdefault(
            atype,
            {"total": 0, "positive": 0, "neutral": 0, "negative": 0, "rev_deltas": [], "margins": []},
        )
        entry["total"] += 1
        entry[r.outcome_status] += 1
        if r.actual_revenue_delta_pct is not None:
            entry["rev_deltas"].append(r.actual_revenue_delta_pct)
        if r.actual_margin_pct is not None:
            entry["margins"].append(r.actual_margin_pct)

    type_summary: dict[str, Any] = {}
    for atype, stats in by_type.items():
        win_rate = stats["positive"] / stats["total"]
        confidence_signal = "boost" if win_rate >= 0.6 else ("cautious" if stats["negative"] > stats["positive"] else "normal")
        type_summary[atype] = {
            "total": stats["total"],
            "positive": stats["positive"],
            "neutral": stats["neutral"],
            "negative": stats["negative"],
            "win_rate_pct": round(win_rate * 100, 1),
            "avg_revenue_delta_pct": round(sum(stats["rev_deltas"]) / len(stats["rev_deltas"]), 1) if stats["rev_deltas"] else None,
            "avg_margin_pct": round(sum(stats["margins"]) / len(stats["margins"]), 1) if stats["margins"] else None,
            "confidence_signal": confidence_signal,
        }

    total_pos = sum(1 for r in measured if r.outcome_status == "positive")
    overall_win = round((total_pos / len(measured)) * 100, 1) if measured else None
    recent_citations = [
        {
            "id": r.id,
            "title": r.title,
            "action_type": r.action_type or "general",
            "outcome_status": r.outcome_status,
            "actual_units_ordered": r.actual_units_ordered,
            "actual_revenue_delta_pct": r.actual_revenue_delta_pct,
            "actual_margin_pct": r.actual_margin_pct,
            "outcome_notes": r.outcome_notes,
        }
        for r in measured[:5]
    ]

    return {
        "seller_id": seller_id,
        "measured_count": len(measured),
        "positive_count": total_pos,
        "overall_win_rate_pct": overall_win,
        "by_action_type": type_summary,
        "recent_outcomes": recent_citations,
        "data_status": "observed",
    }


def _estimate_sku_daily_velocity(db: Session, seller_id: str, sku_id: str, lookback_days: int = 60) -> float:
    end_date = date.today()
    start_date = end_date - timedelta(days=lookback_days - 1)
    rows = (
        db.query(DailyPerformance)
        .filter(
            DailyPerformance.seller_id == seller_id,
            DailyPerformance.sku_id == sku_id,
            DailyPerformance.perf_date >= start_date,
            DailyPerformance.perf_date <= end_date,
        )
        .all()
    )
    active_units = [r.units_sold for r in rows if not r.stockout_indicator and r.units_sold > 0]
    if active_units:
        return sum(active_units) / len(active_units)
    total_units = sum(r.units_sold for r in rows)
    return total_units / max(1, len(rows)) if rows else 0.5


def _days_to_next_festival(db: Session) -> tuple[Optional[int], Optional[str]]:
    today = date.today()
    upcoming = (
        db.query(CalendarEvent)
        .filter(CalendarEvent.end_date >= today)
        .order_by(CalendarEvent.start_date)
        .first()
    )
    if not upcoming:
        return None, None
    days_away = max(0, (upcoming.start_date - today).days)
    return days_away, upcoming.event_name


def simulate_what_if_scenario(
    db: Session,
    seller_id: str,
    budget_inr: float = 15000.0,
    sku_id: Optional[str] = None,
    delay_days: int = 7,
    festival_uplift_pct: float = 25.0,
) -> dict[str, Any]:
    """Simulate spending ₹budget_inr on restocking now vs delaying replenishment."""
    seller = db.query(Seller).filter(Seller.id == seller_id).first()
    if not seller:
        return {"error": f"Seller {seller_id} not found"}

    products = (
        db.query(Product)
        .filter(Product.seller_id == seller_id, Product.active == True)  # noqa: E712
        .all()
    )
    if sku_id:
        matched = [
            p for p in products
            if p.id.lower() == sku_id.lower()
            or p.sku_code.lower() == sku_id.lower()
            or sku_id.lower() in p.title.lower()
        ]
        candidates = matched or products
    else:
        candidates = products

    days_to_fest, fest_name = _days_to_next_festival(db)
    budget_paise = int(round(budget_inr * 100))
    upfront_cash_inr = _inr(seller.available_replenishment_budget)

    # Apply seller decision profile constraints
    risk = (seller.risk_tolerance or "medium").lower()
    priority = (seller.growth_vs_margin_priority or "balanced").lower()
    effective_cap_inr = upfront_cash_inr
    if risk == "high" or (priority == "growth" and seller.supplier_relationship_strength == "strong"):
        stretch = max(seller.max_credit_stretch_pct or 0.0, 0.25)
        effective_cap_inr = round(upfront_cash_inr * (1.0 + stretch), 2)

    within_upfront_budget = budget_inr <= upfront_cash_inr
    within_profile_cap = budget_inr <= effective_cap_inr

    if risk == "low" and not within_upfront_budget:
        profile_guidance = (
            f"Conservative profile active (risk=low): ₹{budget_inr:,.0f} exceeds 100% upfront budget "
            f"(₹{upfront_cash_inr:,.0f}). Recommend capping spend at ₹{upfront_cash_inr:,.0f}."
        )
    elif priority == "growth" and days_to_fest is not None and days_to_fest <= 21:
        profile_guidance = (
            f"Growth profile active ahead of {fest_name} (in {days_to_fest} days): prioritizes festival & "
            f"fast-moving SKUs; supplier strength '{seller.supplier_relationship_strength}' supports up to ₹{effective_cap_inr:,.0f}."
        )
    else:
        profile_guidance = (
            f"Balanced profile (target margin {int((seller.target_margin or 0.25)*100)}%, "
            f"budget ₹{upfront_cash_inr:,.0f}): allocates first to highest-ROI out-of-stock SKUs."
        )

    scored: list[tuple[float, Product, float]] = []
    for p in candidates:
        if p.unit_cost <= 0 or p.selling_price <= 0:
            continue
        vel = _estimate_sku_daily_velocity(db, seller_id, p.id)
        margin = _sku_margin_fraction(p)
        oos_bonus = 2.0 if p.current_stock <= 0 else 1.0
        fest_bonus = (1.0 + festival_uplift_pct / 100.0) if (p.is_festival_sensitive or p.is_wedding_sensitive) else 1.0
        if risk == "low" and seller.target_margin and margin < seller.target_margin:
            continue
        score = vel * margin * oos_bonus * fest_bonus
        scored.append((score, p, vel))

    scored.sort(key=lambda x: x[0], reverse=True)

    remaining_paise = budget_paise
    allocations: list[dict[str, Any]] = []
    total_units = 0
    total_expected_rev_paise = 0
    total_expected_profit_paise = 0
    total_delay_loss_paise = 0
    weighted_cover_days = 0.0

    cover_cap = 10 if risk == "low" else (seller.preferred_stock_cover_days or 14)

    for _, prod, base_vel in scored:
        if remaining_paise < prod.unit_cost * max(1, prod.minimum_order_quantity):
            continue
        uplift_factor = (
            1.0 + (festival_uplift_pct / 100.0)
            if (days_to_fest is not None and days_to_fest <= 21 and (prod.is_festival_sensitive or prod.is_wedding_sensitive))
            else 1.0
        )
        eff_vel = max(0.3, base_vel * uplift_factor)
        desired_units = max(prod.minimum_order_quantity, int(round(eff_vel * cover_cap)))
        max_affordable = remaining_paise // prod.unit_cost
        qty = min(desired_units, max_affordable)
        if not sku_id and len(scored) >= 3 and qty > max_affordable and max_affordable >= prod.minimum_order_quantity:
            qty = max_affordable
        if qty < prod.minimum_order_quantity:
            continue

        cost_paise = qty * prod.unit_cost
        rev_paise = qty * prod.selling_price
        profit_paise = qty * max(0, prod.selling_price - prod.unit_cost)
        delay_lost_units = min(qty, int(round(eff_vel * delay_days)))
        delay_loss_paise = delay_lost_units * prod.selling_price

        remaining_paise -= cost_paise
        total_units += qty
        total_expected_rev_paise += rev_paise
        total_expected_profit_paise += profit_paise
        total_delay_loss_paise += delay_loss_paise
        weighted_cover_days = max(weighted_cover_days, round(qty / eff_vel, 1))

        allocations.append({
            "sku_id": prod.id,
            "sku_code": prod.sku_code,
            "title": prod.title,
            "seasonality_tag": prod.seasonality_tag or "evergreen",
            "lead_time_days": prod.supplier_lead_time_days,
            "units_to_order": qty,
            "cost_inr": _inr(cost_paise),
            "expected_revenue_inr": _inr(rev_paise),
            "expected_profit_inr": _inr(profit_paise),
            "margin_pct": round(_sku_margin_fraction(prod) * 100, 1),
            "delay_risk_inr": _inr(delay_loss_paise),
        })
        if remaining_paise <= 0:
            break

    spent_paise = budget_paise - remaining_paise
    spent_inr = _inr(spent_paise)
    rev_inr = _inr(total_expected_rev_paise)
    profit_inr = _inr(total_expected_profit_paise)
    projected_margin = round((total_expected_profit_paise / total_expected_rev_paise) * 100, 1) if total_expected_rev_paise > 0 else 0.0
    roi = round(rev_inr / spent_inr, 2) if spent_inr > 0 else 0.0

    # Weighted avg payback based on daily profit velocity
    daily_rev_inr = sum(
        (_estimate_sku_daily_velocity(db, seller_id, a["sku_id"]) * next(p.selling_price for _, p, _ in scored if p.id == a["sku_id"])) / 100.0
        for a in allocations
    )
    payback_days = round(spent_inr / max(1.0, daily_rev_inr), 1) if spent_inr > 0 else 0.0

    return {
        "seller_id": seller_id,
        "scenario_inputs": {
            "requested_budget_inr": budget_inr,
            "sku_id": sku_id,
            "delay_days": delay_days,
            "festival_uplift_pct": festival_uplift_pct,
        },
        "actual_allocated_spend_inr": spent_inr,
        "unspent_budget_inr": _inr(remaining_paise),
        "units_procured": total_units,
        "expected_revenue_uplift_inr": rev_inr,
        "expected_gross_profit_inr": profit_inr,
        "projected_margin_pct": projected_margin,
        "roi_multiple": roi,
        "estimated_payback_days": payback_days,
        "delay_opportunity_cost_inr": _inr(total_delay_loss_paise),
        "within_upfront_budget": within_upfront_budget,
        "within_profile_cap": within_profile_cap,
        "profile_guidance": profile_guidance,
        "upcoming_event": fest_name,
        "days_to_event": days_to_fest,
        "sku_allocations": allocations,
        "summary_text": (
            f"Allocating ₹{spent_inr:,.0f} across {len(allocations)} priority SKU(s) ({total_units} units) "
            f"yields ~₹{rev_inr:,.0f} expected revenue with {projected_margin}% margin (~₹{profit_inr:,.0f} gross profit). "
            f"Delaying restock by {delay_days} days risks ~₹{_inr(total_delay_loss_paise):,.0f} in lost sales."
        ),
        "data_status": "simulated",
    }


def build_smart_replenishment_plan(
    db: Session,
    seller_id: str,
    auto_create_recommendation: bool = False,
) -> dict[str, Any]:
    """Build profile-aware, lead-time-adjusted replenishment plan across active SKUs."""
    seller = db.query(Seller).filter(Seller.id == seller_id).first()
    if not seller:
        return {"error": f"Seller {seller_id} not found"}

    track = get_outcome_track_record(db, seller_id)
    restock_track = track["by_action_type"].get("restock", {})
    confidence_signal = restock_track.get("confidence_signal", "normal")

    risk = (seller.risk_tolerance or "medium").lower()
    priority = (seller.growth_vs_margin_priority or "balanced").lower()
    base_budget_inr = _inr(seller.available_replenishment_budget)
    stretch = seller.max_credit_stretch_pct or 0.0
    if risk == "low" or priority == "margin":
        max_budget_inr = base_budget_inr
    elif risk == "high" or (priority == "growth" and seller.supplier_relationship_strength == "strong"):
        max_budget_inr = round(base_budget_inr * (1.0 + max(stretch, 0.25)), 2)
    else:
        max_budget_inr = round(base_budget_inr * (1.0 + min(stretch, 0.15)), 2)

    days_to_fest, fest_name = _days_to_next_festival(db)
    target_cover = min(seller.preferred_stock_cover_days or 14, 10) if risk == "low" else (seller.preferred_stock_cover_days or 14)

    products = (
        db.query(Product)
        .filter(Product.seller_id == seller_id, Product.active == True)  # noqa: E712
        .all()
    )

    items: list[dict[str, Any]] = []
    for p in products:
        vel = _estimate_sku_daily_velocity(db, seller_id, p.id)
        if vel <= 0:
            continue
        effective_stock = p.current_stock + p.incoming_stock
        cover_days = round(effective_stock / vel, 1)
        margin = _sku_margin_fraction(p)
        if risk == "low" and seller.target_margin and margin < seller.target_margin:
            continue

        # Must order if cover < target_cover + lead_time
        need_horizon = p.supplier_lead_time_days + target_cover
        if cover_days >= need_horizon:
            continue

        fest_multiplier = (
            1.25
            if (days_to_fest is not None and days_to_fest <= p.supplier_lead_time_days + 14 and (p.is_festival_sensitive or p.is_wedding_sensitive))
            else 1.0
        )
        raw_needed = max(0, int(round(vel * fest_multiplier * (p.supplier_lead_time_days + min(7, target_cover)))) - effective_stock)
        if raw_needed == 0:
            continue
        qty = max(p.minimum_order_quantity, raw_needed)
        cost_inr = _inr(qty * p.unit_cost)
        expected_rev_inr = _inr(qty * p.selling_price)
        urgency_score = (vel * p.selling_price / 100.0) * (2.0 if p.current_stock <= 0 else 1.2) * (1.3 if p.supplier_lead_time_days >= 9 else 1.0) * fest_multiplier
        if confidence_signal == "boost":
            urgency_score *= 1.15

        items.append({
            "sku_id": p.id,
            "sku_code": p.sku_code,
            "title": p.title,
            "category": p.category,
            "demand_segment": p.demand_segment,
            "seasonality_tag": p.seasonality_tag or "evergreen",
            "current_stock": p.current_stock,
            "incoming_stock": p.incoming_stock,
            "cover_days": cover_days,
            "supplier_lead_time_days": p.supplier_lead_time_days,
            "daily_velocity": round(vel, 2),
            "recommended_qty": qty,
            "unit_cost_inr": _inr(p.unit_cost),
            "selling_price_inr": _inr(p.selling_price),
            "moq": p.minimum_order_quantity,
            "cost_inr": cost_inr,
            "expected_revenue_inr": expected_rev_inr,
            "margin_pct": round(margin * 100, 1),
            "priority_score": round(urgency_score, 1),
        })

    items.sort(key=lambda x: x["priority_score"], reverse=True)

    selected: list[dict[str, Any]] = []
    remaining = max_budget_inr
    for item in items:
        if item["cost_inr"] <= remaining:
            selected.append(item)
            remaining = round(remaining - item["cost_inr"], 2)
        elif item["unit_cost_inr"] > 0:
            affordable_qty = int(remaining // item["unit_cost_inr"])
            if affordable_qty >= item["moq"]:
                partial = dict(item)
                partial["recommended_qty"] = affordable_qty
                partial["cost_inr"] = round(affordable_qty * item["unit_cost_inr"], 2)
                partial["expected_revenue_inr"] = round(affordable_qty * item["selling_price_inr"], 2)
                selected.append(partial)
                remaining = round(remaining - partial["cost_inr"], 2)

    total_cost = round(sum(x["cost_inr"] for x in selected), 2)
    total_rev = round(sum(x["expected_revenue_inr"] for x in selected), 2)

    created_rec_id: Optional[str] = None
    if auto_create_recommendation and selected:
        sku_names = ", ".join(x["title"] for x in selected[:3])
        rec = Recommendation(
            seller_id=seller_id,
            title=f"Smart Auto-Replenishment PO ({len(selected)} priority SKUs · ₹{total_cost:,.0f})",
            problem_or_opportunity=(
                f"{len(items)} active SKUs sit below safe cover ({target_cover}d + supplier lead time). "
                f"Priority stockouts like {sku_names} need immediate PO placement."
            ),
            suggested_action=(
                f"Approve batch PO for {len(selected)} SKUs ({sum(x['recommended_qty'] for x in selected)} units) "
                f"costing ₹{total_cost:,.0f} within {risk}-risk budget cap ₹{max_budget_inr:,.0f}."
            ),
            expected_impact=f"Projected revenue recovery ~₹{total_rev:,.0f}.",
            cost_or_budget=int(round(total_cost * 100)),
            risk="low" if total_cost <= base_budget_inr else "medium",
            confidence="high" if confidence_signal == "boost" else "medium",
            urgency="high",
            priority=1,
            action_type="restock",
            assumptions=f"Profile={risk}/{priority}; lead-time adjusted; outcome signal={confidence_signal}.",
            what_to_measure_next="7-day stockout reduction and realized margin vs 25% target.",
            requires_approval=True,
            approval_status="pending",
            execution_status="not_started",
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        created_rec_id = rec.id

    return {
        "seller_id": seller_id,
        "seller_profile": {
            "risk_tolerance": risk,
            "growth_vs_margin_priority": priority,
            "upfront_budget_inr": base_budget_inr,
            "profile_cap_inr": max_budget_inr,
            "outcome_confidence_signal": confidence_signal,
        },
        "upcoming_event": fest_name,
        "days_to_event": days_to_fest,
        "candidates_needing_restock": len(items),
        "recommended_batch": selected,
        "batch_total_cost_inr": total_cost,
        "batch_expected_revenue_inr": total_rev,
        "created_recommendation_id": created_rec_id,
        "data_status": "calculated",
    }


def generate_proactive_alerts(
    db: Session,
    seller_id: str,
    channel: str = "in_app",
    persist: bool = True,
) -> list[dict[str, Any]]:
    """Run deterministic KAM risk checks and optionally persist deduplicated alerts."""
    seller = db.query(Seller).filter(Seller.id == seller_id).first()
    if not seller:
        return []

    today = date.today()
    products = (
        db.query(Product)
        .filter(Product.seller_id == seller_id, Product.active == True)  # noqa: E712
        .all()
    )
    days_to_fest, fest_name = _days_to_next_festival(db)

    candidate_alerts: list[dict[str, Any]] = []

    # 1. Stockout Impact Alert (top censored demand loss)
    oos_impact = calculate_stockout_impact(db, seller_id, period_days=30, as_of=today)
    if oos_impact["top_impacted_skus"]:
        top = oos_impact["top_impacted_skus"][0]
        candidate_alerts.append({
            "alert_type": "lost_sales",
            "severity": "high",
            "title": f"High lost sales on {top['title']} (~₹{top['lost_revenue_inr']:,.0f})",
            "message": (
                f"{top['sku_code']} ({top['title']}) had {top['stockout_days']} stockout days at "
                f"{top['avg_daily_velocity']}/day velocity — losing ~{top['lost_units']} units (≈₹{top['lost_revenue_inr']:,.0f}). "
                f"Supplier lead time is {top['supplier_lead_time_days']} days."
            ),
            "spoken_message": (
                f"Urgent alert: {top['title']} lost around {top['lost_units']} units worth "
                f"{int(round(top['lost_revenue_inr']))} rupees due to stockouts, and its supplier needs "
                f"{top['supplier_lead_time_days']} days to deliver."
            ),
            "related_sku_id": top["sku_id"],
            "estimated_impact_inr": int(round(top["lost_revenue_inr"])),
        })

    # 2. Imminent Low Cover vs Supplier Lead Time (in-stock SKUs about to stock out)
    low_cover_candidates: list[dict[str, Any]] = []
    for p in products:
        if p.current_stock <= 0:
            continue
        vel = _estimate_sku_daily_velocity(db, seller_id, p.id)
        if vel <= 0.3:
            continue
        cover = p.current_stock / vel
        if cover <= p.supplier_lead_time_days + 4:
            at_risk_inr = int(round(vel * max(5, p.supplier_lead_time_days) * p.selling_price / 100.0))
            low_cover_candidates.append({
                "p": p,
                "cover": round(cover, 1),
                "at_risk_inr": at_risk_inr,
            })
    low_cover_candidates.sort(key=lambda x: x["cover"])
    if low_cover_candidates:
        c = low_cover_candidates[0]
        p = c["p"]
        candidate_alerts.append({
            "alert_type": "stockout_risk",
            "severity": "high" if c["cover"] <= p.supplier_lead_time_days else "medium",
            "title": f"Low stock cover on {p.title} ({c['cover']} days left)",
            "message": (
                f"{p.title} has only {c['cover']} days of stock cover ({p.current_stock} units), "
                f"while supplier lead time is {p.supplier_lead_time_days} days. Order now to avoid losing ~₹{c['at_risk_inr']:,.0f}."
            ),
            "spoken_message": (
                f"{p.title} has only {c['cover']} days of stock left, compared to a {p.supplier_lead_time_days} day supplier lead time."
            ),
            "related_sku_id": p.id,
            "estimated_impact_inr": c["at_risk_inr"],
        })

    # 3. Recent 3-day Cancellation Spike Check
    recent_start = today - timedelta(days=3)
    recent_rows = (
        db.query(DailyPerformance)
        .filter(
            DailyPerformance.seller_id == seller_id,
            DailyPerformance.perf_date >= recent_start,
            DailyPerformance.perf_date <= today,
        )
        .all()
    )
    cancel_agg: dict[str, dict[str, int]] = {}
    for r in recent_rows:
        agg = cancel_agg.setdefault(r.sku_id, {"orders": 0, "cancellations": 0})
        agg["orders"] += r.orders
        agg["cancellations"] += r.cancellations

    prod_map = {p.id: p for p in products}
    spiked = []
    for sid, vals in cancel_agg.items():
        if vals["orders"] >= 3:
            rate = vals["cancellations"] / vals["orders"]
            if rate >= 0.14:
                spiked.append((rate, sid, vals))
    spiked.sort(key=lambda x: x[0], reverse=True)
    if spiked:
        rate, sid, vals = spiked[0]
        p = prod_map.get(sid)
        name = p.title if p else sid
        impact_inr = int(round(vals["cancellations"] * (_inr(p.selling_price) if p else 500)))
        candidate_alerts.append({
            "alert_type": "cancellation_spike",
            "severity": "high",
            "title": f"Cancellation spike on {name} ({rate*100:.0f}% last 3 days)",
            "message": (
                f"{name} saw {vals['cancellations']} cancellations on {vals['orders']} orders ({rate*100:.0f}%) in the last 3 days. "
                "Audit dispatch partner pickup SLAs and inventory buffer immediately."
            ),
            "spoken_message": (
                f"Cancellation rate on {name} spiked to {round(rate*100)} percent in the last 3 days. Check dispatch pickup and stock sync."
            ),
            "related_sku_id": sid,
            "estimated_impact_inr": impact_inr,
        })

    # 4. Upcoming Festival / Payday Readiness Alert
    if days_to_fest is not None and days_to_fest <= 21:
        sensitive = [p for p in products if p.is_festival_sensitive or p.is_wedding_sensitive]
        under_covered = []
        for p in sensitive:
            vel = _estimate_sku_daily_velocity(db, seller_id, p.id)
            cover = (p.current_stock / vel) if vel > 0 else (99.0 if p.current_stock > 0 else 0.0)
            if cover < max(10, p.supplier_lead_time_days + 4):
                under_covered.append(p)
        if under_covered:
            est = int(round(sum(_estimate_sku_daily_velocity(db, seller_id, p.id) * 5 * p.selling_price / 100.0 for p in under_covered[:5])))
            candidate_alerts.append({
                "alert_type": "festival_readiness",
                "severity": "high",
                "title": f"{fest_name} in {days_to_fest} days: {len(under_covered)} key SKUs below safe cover",
                "message": (
                    f"{fest_name} starts in {days_to_fest} days. {len(under_covered)} festival/wedding-sensitive SKUs "
                    f"(including {under_covered[0].title}) have <10 days cover vs 3–14 day supplier lead times."
                ),
                "spoken_message": (
                    f"{fest_name} is in {days_to_fest} days, and {len(under_covered)} festival sensitive products are running low on cover."
                ),
                "related_sku_id": under_covered[0].id,
                "estimated_impact_inr": est,
            })

    if not persist:
        return candidate_alerts

    # Deduplicate against non-dismissed alerts created in last 24h
    cutoff = datetime.utcnow() - timedelta(hours=24)
    existing = (
        db.query(ProactiveAlert)
        .filter(
            ProactiveAlert.seller_id == seller_id,
            ProactiveAlert.dismissed == False,  # noqa: E712
            ProactiveAlert.created_at >= cutoff,
        )
        .all()
    )
    existing_keys = {(a.alert_type, a.related_sku_id) for a in existing}

    for item in candidate_alerts:
        key = (item["alert_type"], item.get("related_sku_id"))
        if key in existing_keys:
            continue
        db.add(
            ProactiveAlert(
                seller_id=seller_id,
                alert_type=item["alert_type"],
                severity=item["severity"],
                title=item["title"],
                message=item["message"],
                spoken_message=item.get("spoken_message"),
                related_sku_id=item.get("related_sku_id"),
                estimated_impact_inr=item.get("estimated_impact_inr"),
                is_read=False,
                dismissed=False,
                delivered_channel=channel,
            )
        )
    db.commit()

    all_active = (
        db.query(ProactiveAlert)
        .filter(ProactiveAlert.seller_id == seller_id, ProactiveAlert.dismissed == False)  # noqa: E712
        .order_by(ProactiveAlert.created_at.desc())
        .all()
    )
    return [
        {
            "id": a.id,
            "seller_id": a.seller_id,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "title": a.title,
            "message": a.message,
            "spoken_message": a.spoken_message,
            "related_sku_id": a.related_sku_id,
            "estimated_impact_inr": a.estimated_impact_inr,
            "is_read": a.is_read,
            "dismissed": a.dismissed,
            "delivered_channel": a.delivered_channel,
            "created_at": a.created_at.isoformat(),
        }
        for a in all_active
    ]
