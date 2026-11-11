"""Tests for Phases 1-4 Intelligence Engine, Multi-Agent Coordinator, and API routes."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.agent.specialists import (
    build_specialist_briefs,
    collect_tools_for_specialists,
    parse_what_if_params,
    route_query_to_specialists,
)
from app.main import app
from app.models import (
    CalendarEvent,
    DailyPerformance,
    ProactiveAlert,
    Product,
    Recommendation,
    Seller,
)
from app.services.intelligence import (
    build_smart_replenishment_plan,
    calculate_stockout_impact,
    decompose_revenue_change,
    generate_proactive_alerts,
    get_outcome_track_record,
    simulate_what_if_scenario,
)


def _seed_rich_seller(db, risk_tolerance: str = "medium", priority: str = "balanced") -> Seller:
    seller = Seller(
        id="intel-seller-001",
        display_name="Intel Test Store",
        marketplace="Snapdeal",
        state="Maharashtra",
        city="Pune",
        timezone="Asia/Kolkata",
        target_margin=0.25,
        available_replenishment_budget=2000000,  # ₹20,000
        risk_tolerance=risk_tolerance,
        growth_vs_margin_priority=priority,
        supplier_relationship_strength="strong",
        max_credit_stretch_pct=0.25,
        preferred_stock_cover_days=14,
    )
    db.add(seller)
    db.commit()

    # SKU 1: Fast-moving stocked-out festive product (long lead time = 10d, 35% margin)
    p1 = Product(
        id="i-sku-1",
        seller_id=seller.id,
        sku_code="SD-TST-001",
        title="Basmati Rice 5kg",
        category="Grocery",
        subcategory="Staples",
        selling_price=50000,  # ₹500
        unit_cost=32500,      # ₹325 (35% margin)
        minimum_margin=0.20,
        current_stock=0,
        supplier_lead_time_days=10,
        minimum_order_quantity=10,
        seasonality_tag="festival",
        demand_segment="staple",
        is_festival_sensitive=True,
        is_payday_sensitive=True,
    )
    # SKU 2: In-stock low-cover product with 3-day cancellation spike
    p2 = Product(
        id="i-sku-2",
        seller_id=seller.id,
        sku_code="SD-TST-002",
        title="Toor Dal 2kg",
        category="Grocery",
        subcategory="Staples",
        selling_price=40000,  # ₹400
        unit_cost=32000,      # ₹320 (20% margin - below 25% floor)
        minimum_margin=0.15,
        current_stock=6,      # ~2 days of stock vs 7d lead time!
        supplier_lead_time_days=7,
        minimum_order_quantity=5,
        seasonality_tag="payday",
        demand_segment="staple",
        is_payday_sensitive=True,
    )
    db.add_all([p1, p2])
    db.commit()

    today = date.today()
    # Prior 30 days: p1 sold 10/day cleanly, p2 sold 3/day
    for offset in range(30, 60):
        d = today - timedelta(days=offset)
        db.add(DailyPerformance(
            seller_id=seller.id, sku_id=p1.id, perf_date=d,
            units_sold=10, gross_sales=500000, net_sales=500000,
            orders=10, cancellations=0, returns=0, stockout_indicator=False,
        ))
        db.add(DailyPerformance(
            seller_id=seller.id, sku_id=p2.id, perf_date=d,
            units_sold=3, gross_sales=120000, net_sales=120000,
            orders=3, cancellations=0, returns=0, stockout_indicator=False,
        ))

    # Current 30 days: p1 stocked out first 10 days; p2 sold 3/day with high cancellations last 3 days
    for offset in range(0, 30):
        d = today - timedelta(days=offset)
        p1_oos = offset < 10
        db.add(DailyPerformance(
            seller_id=seller.id, sku_id=p1.id, perf_date=d,
            units_sold=0 if p1_oos else 10,
            gross_sales=0 if p1_oos else 500000,
            net_sales=0 if p1_oos else 500000,
            orders=0 if p1_oos else 10,
            cancellations=0, returns=0, stockout_indicator=p1_oos,
        ))
        recent_spike = offset <= 2
        db.add(DailyPerformance(
            seller_id=seller.id, sku_id=p2.id, perf_date=d,
            units_sold=3, gross_sales=120000, net_sales=120000,
            orders=4 if recent_spike else 3,
            cancellations=2 if recent_spike else 0,
            returns=0, stockout_indicator=False,
        ))

    # Upcoming festival in 12 days
    db.add(CalendarEvent(
        event_name="Diwali Peak",
        event_type="festival",
        start_date=today + timedelta(days=12),
        end_date=today + timedelta(days=16),
        geography="India",
        shopping_lead_in_days=14,
        confidence="verified",
    ))

    # Past positive outcome recommendation
    db.add(Recommendation(
        id="hist-rec-1",
        seller_id=seller.id,
        title="Past Rice Restock",
        problem_or_opportunity="Low stock",
        suggested_action="Order 100 units",
        action_type="restock",
        approval_status="approved",
        execution_status="executed",
        outcome_status="positive",
        actual_units_ordered=100,
        actual_revenue_delta_pct=30.0,
        actual_margin_pct=28.0,
    ))
    db.commit()
    return seller


def test_stockout_impact_and_root_cause_decomposition(db_session):
    seller = _seed_rich_seller(db_session)
    oos = calculate_stockout_impact(db_session, seller.id, period_days=30)
    assert oos["affected_sku_count"] == 1
    assert oos["total_lost_units"] == 100  # 10 days * 10 units/day
    assert oos["total_lost_revenue_inr"] == 50000.0
    assert oos["top_impacted_skus"][0]["title"] == "Basmati Rice 5kg"

    decomp = decompose_revenue_change(db_session, seller.id, period_days=30)
    comp = decomp["components"]
    exact_identity = comp["volume_effect_inr"] + comp["price_effect_inr"] + comp["interaction_effect_inr"]
    assert abs(exact_identity - decomp["revenue_change_inr"]) < 1.0
    assert decomp["drivers"]["availability_stockout_loss_inr"] > 0


def test_what_if_and_seller_decision_profile(db_session):
    low_risk = _seed_rich_seller(db_session, risk_tolerance="low", priority="margin")
    sim_over = simulate_what_if_scenario(db_session, low_risk.id, budget_inr=25000.0, delay_days=7)
    assert sim_over["within_upfront_budget"] is False
    assert "Conservative profile" in sim_over["profile_guidance"]
    # Low-risk + target_margin=0.25 excludes 20% margin p2 and invests in 35% margin p1
    assert all(a["margin_pct"] >= 25.0 for a in sim_over["sku_allocations"])
    assert sim_over["expected_revenue_uplift_inr"] > sim_over["actual_allocated_spend_inr"]
    assert sim_over["delay_opportunity_cost_inr"] > 0

    plan = build_smart_replenishment_plan(db_session, low_risk.id, auto_create_recommendation=True)
    assert plan["seller_profile"]["outcome_confidence_signal"] == "boost"
    assert plan["created_recommendation_id"] is not None


def test_proactive_alerts_deduplication_and_outcome_memory(db_session):
    seller = _seed_rich_seller(db_session)
    alerts = generate_proactive_alerts(db_session, seller.id, persist=True)
    types = {a["alert_type"] for a in alerts}
    assert "lost_sales" in types
    assert "stockout_risk" in types
    assert "cancellation_spike" in types
    assert "festival_readiness" in types

    # Running a second time within 24h must not create duplicate alerts
    count_before = db_session.query(ProactiveAlert).filter(ProactiveAlert.seller_id == seller.id).count()
    generate_proactive_alerts(db_session, seller.id, persist=True)
    count_after = db_session.query(ProactiveAlert).filter(ProactiveAlert.seller_id == seller.id).count()
    assert count_after == count_before

    track = get_outcome_track_record(db_session, seller.id)
    assert track["measured_count"] == 1
    assert track["overall_win_rate_pct"] == 100.0


def test_multi_agent_specialist_routing_and_params(db_session):
    seller = _seed_rich_seller(db_session)
    sp_whatif = route_query_to_specialists("What if I spend ₹10k on restocking vs delaying 1 week?")
    assert "finance_kam" in sp_whatif
    assert "inventory_kam" in sp_whatif
    params = parse_what_if_params("What if I spend ₹10k and delay 2 weeks?")
    assert params["budget_inr"] == 10000.0
    assert params["delay_days"] == 14

    tools = collect_tools_for_specialists(sp_whatif, [])
    assert "simulate_what_if_scenario" in tools
    assert "get_smart_replenishment_plan" in tools

    oos = calculate_stockout_impact(db_session, seller.id, 30)
    decomp = decompose_revenue_change(db_session, seller.id, 30)
    briefs = build_specialist_briefs(
        ["sales_kam", "inventory_kam", "finance_kam"],
        {"decompose_revenue_change": decomp, "calculate_stockout_impact": oos},
        {"risk_tolerance": "medium", "growth_vs_margin_priority": "balanced"},
    )
    assert "[Sales KAM]:" in briefs
    assert "[Inventory KAM]:" in briefs
    assert "[Finance KAM]:" in briefs


def test_new_analytics_alerts_and_outcome_api_endpoints(db_session):
    from app.api.alerts import dismiss_alert, list_alerts, run_digest_now
    from app.api.analytics import get_revenue_decomposition, get_stockout_impact, run_what_if_simulation
    from app.api.chat import get_conversation_memories
    from app.api.forecast import get_smart_replenishment_plan
    from app.api.recommendations import get_recommendations_track_record, record_recommendation_outcome
    from app.schemas import OutcomeRecord, WhatIfRequest

    paths = set(app.openapi()["paths"].keys())
    for expected in (
        "/api/alerts",
        "/api/alerts/run-digest",
        "/api/alerts/{alert_id}/dismiss",
        "/api/analytics/stockout-impact",
        "/api/analytics/decomposition",
        "/api/analytics/what-if",
        "/api/forecasts/replenishment/smart",
        "/api/recommendations/{rec_id}/outcome",
        "/api/recommendations/track-record",
        "/api/assistant/memory",
    ):
        assert expected in paths

    seller = _seed_rich_seller(db_session)
    decomp = get_revenue_decomposition(period_days=30, seller_id=seller.id, db=db_session)
    assert "summary_text" in decomp

    oos = get_stockout_impact(period_days=30, seller_id=seller.id, db=db_session)
    assert oos["total_lost_units"] == 100

    wif = run_what_if_simulation(
        WhatIfRequest(budget_inr=15000, delay_days=7),
        seller_id=seller.id,
        db=db_session,
    )
    assert wif["expected_revenue_uplift_inr"] > 0

    smart = get_smart_replenishment_plan(auto_create=False, seller_id=seller.id, db=db_session)
    assert len(smart["recommended_batch"]) >= 1

    alerts_list = run_digest_now(channel="in_app", seller_id=seller.id, db=db_session)
    assert len(alerts_list) >= 3
    assert len(list_alerts(seller_id=seller.id, db=db_session)) == len(alerts_list)

    dismissed = dismiss_alert(alerts_list[0].id, seller_id=seller.id, db=db_session)
    assert dismissed.dismissed is True

    updated_rec = record_recommendation_outcome(
        "hist-rec-1",
        OutcomeRecord(
            outcome_status="positive",
            actual_units_ordered=150,
            actual_revenue_delta_pct=32.0,
            actual_margin_pct=29.0,
            outcome_notes="Confirmed uplift",
        ),
        seller_id=seller.id,
        db=db_session,
    )
    assert updated_rec.actual_units_ordered == 150
    track = get_recommendations_track_record(seller_id=seller.id, db=db_session)
    assert track["overall_win_rate_pct"] == 100.0

    # Verify memory route exists and calls store cleanly
    assert callable(get_conversation_memories)


def test_conversation_memory_persistence_and_recall(db_session):
    from app.memory.extractor import extract_facts_from_turn
    from app.memory.store import (
        format_memory_context,
        load_session_history,
        recall_conversation_memories,
        store_conversation_turn,
    )

    seller = _seed_rich_seller(db_session)
    tool_results = {
        "calculate_stockout_impact": {
            "affected_sku_count": 1,
            "total_lost_revenue_inr": 50000.0,
            "top_impacted_skus": [{"sku_code": "SD-TST-001", "title": "Basmati Rice 5kg"}],
            "summary_text": "Lost 100 units (~₹50,000) due to Basmati Rice stockout",
        }
    }
    facts = extract_facts_from_turn(
        user_message="Why are my sales down this month? My budget is ₹40,000.",
        assistant_response="Revenue down primarily from stockouts on SD-TST-001. I recommend restocking 100 units first.",
        tool_results=tool_results,
    )
    assert "SD-TST-001" in facts["related_sku_ids"]
    assert "50,000" in facts["problem_summary"]
    assert "40,000" in facts["key_takeaway"]

    saved = store_conversation_turn(
        seller_id=seller.id,
        conversation_id="conv-mem-1",
        turn_number=1,
        user_message="Why are my sales down this month? My budget is ₹40,000.",
        assistant_response="Revenue down due to SD-TST-001 Basmati Rice stockout.",
        tool_results=tool_results,
        db=db_session,
    )
    assert saved.id is not None

    recalled = recall_conversation_memories(
        seller.id,
        query="What should I restock before Diwali for Basmati Rice?",
        db=db_session,
    )
    assert len(recalled) >= 1
    assert "SD-TST-001" in (recalled[0]["related_sku_ids"] or "")
    ctx = format_memory_context(recalled)
    assert "Basmati Rice" in ctx or "SD-TST-001" in ctx

    rehydrated = load_session_history(seller.id, "conv-mem-1", db=db_session)
    assert len(rehydrated) == 2
    assert rehydrated[0]["role"] == "user"
    assert rehydrated[1]["role"] == "assistant"
