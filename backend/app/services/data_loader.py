"""Deterministic mock data loader for the Virtual KAM demo.

Seeds one Snapdeal marketplace seller with 30 SKUs across 4 Indian ecommerce
categories, 180 days of daily performance, inventory snapshots, calendar events,
and initial approval-pending recommendations.

Headline figures reconcile directly to the Snapdeal Virtual KAM scenario:
- Last month sales: ₹2,00,000; this month: ₹1,35,000 (-32.5%)
- Orders: 400 → 270 (-32.5%)
- Cancellation rate: 8% (32/400) → 14% (38/270)
- Average selling price: ₹500 unchanged
- Out-of-stock products: 5 → 18 (18 of 30 active SKUs currently at 0 stock)

Currency: integer paise. Dates: Asia/Kolkata.
"""

from datetime import date, datetime, timedelta
import json

from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, ensure_schema_columns
from app.models import (
    Base,
    CalendarEvent,
    Conversation,
    ConversationMemory,
    DailyPerformance,
    InventorySnapshot,
    ProactiveAlert,
    Product,
    Recommendation,
    Seller,
)


def _paise(inr: float) -> int:
    return int(round(inr * 100))


def create_demo_data(db: Session) -> None:
    """Seed deterministic demo data. Idempotent: clears existing data first."""

    # Clear existing data (order matters for foreign keys)
    db.query(DailyPerformance).delete()
    db.query(InventorySnapshot).delete()
    db.query(ProactiveAlert).delete()
    db.query(ConversationMemory).delete()
    db.query(Recommendation).delete()
    db.query(Conversation).delete()
    db.query(Product).delete()
    db.query(CalendarEvent).delete()
    db.query(Seller).delete()
    db.commit()

    # ── Seller ────────────────────────────────────────────────────────
    seller = Seller(
        id="demo-seller-001",
        display_name="Rajesh Enterprises (Snapdeal Store)",
        marketplace="Snapdeal (Mock Demo)",
        business_category="Home, Fashion & Lifestyle",
        state="Maharashtra",
        city="Pune",
        serviceable_regions='["Maharashtra", "Karnataka", "Telangana", "Gujarat"]',
        timezone="Asia/Kolkata",
        business_goals="Recover monthly revenue above ₹2,00,000 and bring cancellations under 8% while maintaining ₹500 ASP and >25% margin",
        target_growth=0.25,
        target_margin=0.25,
        available_replenishment_budget=_paise(40000),  # ₹40,000
        risk_tolerance="medium",
        growth_vs_margin_priority="balanced",
        supplier_relationship_strength="standard",
        max_credit_stretch_pct=0.15,
        preferred_stock_cover_days=14,
        storage_capacity=5000,
    )
    db.add(seller)
    db.commit()

    # ── Products / SKUs (30 SKUs: 18 out-of-stock, 12 in-stock) ───────
    # First 5 SKUs (sku-001..005): out of stock since last month (5 stockouts last month)
    # Next 13 SKUs (sku-006..018): sold well last month, stocked out entering this month (18 total stockouts)
    # Remaining 12 SKUs (sku-019..030): currently in stock
    sku_specs = [
        # 5 previously stocked-out SKUs (stock=0)
        ("sku-001", "SD-HOM-001", "Cotton Bedsheet Double (Jaipur Print)", "Home & Kitchen", "Bedding", 500, 340, 0, 5),
        ("sku-002", "SD-FSH-001", "Men's Casual Polo T-Shirt (Navy)", "Fashion", "Apparel", 500, 330, 0, 4),
        ("sku-003", "SD-ELC-001", "Braided USB-C Fast Charging Cable 2-Pack", "Electronics", "Accessories", 450, 290, 0, 3),
        ("sku-004", "SD-PER-001", "Herbal Hair Oil & Shampoo Combo 400ml", "Personal Care", "Hair Care", 550, 370, 0, 4),
        ("sku-005", "SD-HOM-002", "Stainless Steel Insulated Flask 1L", "Home & Kitchen", "Drinkware", 500, 340, 0, 5),
        # 13 newly stocked-out fast-moving SKUs (stock=0 this month, contributed ₹65,000 / 130 orders last month)
        ("sku-006", "SD-FSH-002", "Men's Lightweight Running Shoes", "Fashion", "Footwear", 600, 410, 0, 5),
        ("sku-007", "SD-FSH-003", "Women's Cotton Kurti Set (Festive)", "Fashion", "Ethnic", 400, 270, 0, 4),
        ("sku-008", "SD-HOM-003", "Non-Stick Tawa & Fry Pan Combo", "Home & Kitchen", "Cookware", 550, 380, 0, 5),
        ("sku-009", "SD-HOM-004", "Microfiber Bath Towel Set (Pack of 2)", "Home & Kitchen", "Bath", 450, 300, 0, 3),
        ("sku-010", "SD-ELC-002", "Wireless Bluetooth Neckband Earphones", "Electronics", "Audio", 650, 440, 0, 4),
        ("sku-011", "SD-ELC-003", "Universal Travel Power Adapter", "Electronics", "Power", 350, 230, 0, 3),
        ("sku-012", "SD-PER-002", "Aloe Vera & Neem Face Wash Duo", "Personal Care", "Skin Care", 500, 325, 0, 3),
        ("sku-013", "SD-FSH-004", "Classic Leatherette Bi-Fold Wallet", "Fashion", "Accessories", 500, 330, 0, 3),
        ("sku-014", "SD-HOM-005", "Airtight Kitchen Storage Jars (Set of 6)", "Home & Kitchen", "Storage", 500, 340, 0, 4),
        ("sku-015", "SD-ELC-004", "LED Desk Study Lamp (Rechargeable)", "Electronics", "Lighting", 500, 345, 0, 5),
        ("sku-016", "SD-PER-003", "Ayurvedic Beard Grooming Kit", "Personal Care", "Grooming", 500, 335, 0, 3),
        ("sku-017", "SD-FSH-005", "Unisex Canvas Backpack 25L", "Fashion", "Bags", 550, 375, 0, 5),
        ("sku-018", "SD-HOM-006", "Electric Egg Boiler & Steamer", "Home & Kitchen", "Appliances", 450, 310, 0, 4),
        # 12 currently in-stock SKUs (first 9 drive 270 orders = ₹1,35,000 this month at exact ₹500 ASP)
        ("sku-019", "SD-HOM-007", "Printed Cushion Covers (Set of 5)", "Home & Kitchen", "Decor", 500, 330, 45, 4),
        ("sku-020", "SD-FSH-006", "Men's Stretchable Chino Trousers", "Fashion", "Apparel", 500, 340, 38, 4),
        ("sku-021", "SD-ELC-005", "Foldable Phone & Tablet Stand", "Electronics", "Accessories", 450, 290, 52, 3),
        ("sku-022", "SD-PER-004", "Vitamin C Serum & Sunscreen Pack", "Personal Care", "Skin Care", 550, 360, 40, 3),
        ("sku-023", "SD-FSH-007", "Sports Ankle Socks (Pack of 5)", "Fashion", "Apparel", 400, 250, 60, 2),
        ("sku-024", "SD-HOM-008", "Stainless Steel Spice Box (Masala Dabba)", "Home & Kitchen", "Cookware", 600, 410, 34, 4),
        ("sku-025", "SD-ELC-006", "Silicone Laptop Keyboard Protector & Brush", "Electronics", "Accessories", 350, 210, 55, 2),
        ("sku-026", "SD-FSH-008", "Polarized UV400 Wayfarer Sunglasses", "Fashion", "Eyewear", 650, 420, 28, 3),
        ("sku-027", "SD-PER-005", "Charcoal Peel-Off Mask & Scrub Combo", "Personal Care", "Skin Care", 500, 320, 35, 3),
        # 3 additional in-stock SKUs (low velocity / dead-stock demo candidate)
        ("sku-028", "SD-HOM-009", "Ceramic Coffee Mug Gift Set", "Home & Kitchen", "Drinkware", 500, 340, 22, 4),
        ("sku-029", "SD-FSH-009", "Cotton Canvas Tote Bag", "Fashion", "Bags", 400, 260, 18, 3),
        ("sku-030", "SD-ELC-007", "Wired Optical Mouse (Bulk Stock)", "Electronics", "Peripherals", 500, 350, 240, 2),
    ]

    staple_subcategories = {
        "Hair Care", "Skin Care", "Grooming", "Bath", "Cookware", "Storage", "Power", "Accessories"
    }
    festival_skus = {"sku-001", "sku-006", "sku-007", "sku-010", "sku-014", "sku-019", "sku-024"}
    wedding_skus = {"sku-001", "sku-007", "sku-013", "sku-024", "sku-026", "sku-028"}
    payday_skus = {"sku-004", "sku-008", "sku-009", "sku-012", "sku-014", "sku-016", "sku-022", "sku-023", "sku-027"}
    slow_supplier_lead = {"sku-006": 12, "sku-007": 10, "sku-010": 14, "sku-017": 11, "sku-020": 9}

    products = []
    for pid, code, title, cat, subcat, price_inr, cost_inr, stock, base_lead_days in sku_specs:
        lead_days = slow_supplier_lead.get(pid, base_lead_days)
        is_fest = pid in festival_skus
        is_wed = pid in wedding_skus
        is_payday = pid in payday_skus
        demand_segment = "staple" if subcat in staple_subcategories else "discretionary"

        tags: list[str] = []
        if is_fest:
            tags.append("festival")
        if is_wed:
            tags.append("wedding")
        if is_payday:
            tags.append("payday")
        primary_tag = tags[0] if tags else "evergreen"

        attrs = {
            "demand_segment": demand_segment,
            "seasonality_tag": primary_tag,
            "lead_time_tier": "long_lead" if lead_days >= 9 else ("fast" if lead_days <= 3 else "standard"),
            "peak_windows": tags or ["steady_year_round"],
        }

        products.append(
            Product(
                id=pid,
                seller_id=seller.id,
                sku_code=code,
                title=title,
                category=cat,
                subcategory=subcat,
                selling_price=_paise(price_inr),
                unit_cost=_paise(cost_inr),
                minimum_margin=0.20,
                current_stock=stock,
                reserved_stock=0,
                incoming_stock=20 if pid in ("sku-019", "sku-020") else 0,
                supplier_lead_time_days=lead_days,
                minimum_order_quantity=10,
                seasonality_tags=json.dumps(tags),
                seasonality_tag=primary_tag,
                demand_segment=demand_segment,
                is_festival_sensitive=is_fest,
                is_payday_sensitive=is_payday,
                is_wedding_sensitive=is_wed,
                product_attributes=json.dumps(attrs),
                active=True,
            )
        )

    db.add_all(products)
    db.commit()
    product_map = {p.id: p for p in products}

    # ── Daily performance: 180 days ending today ──────────────────────
    # Current 30-day window (days_from_end 0..29):
    #   - 9 orders/day across sku-019..sku-027 => 270 orders, ₹1,35,000 sales, ₹500 ASP
    #   - 38 cancellations total => 14.07% (displays as 14%)
    #   - 18 SKUs (sku-001..018) at 0 stock
    # Previous 30-day window (days_from_end 30..59):
    #   - Same 9 orders/day on sku-019..sku-027 (270 orders, ₹1,35,000)
    #   - PLUS 130 orders / ₹65,000 from sku-006..018 (weighted at exact ₹500 ASP)
    #   - Total = 400 orders, ₹2,00,000 sales, ₹500 ASP
    #   - 32 cancellations total => 8.0%
    #   - 5 SKUs (sku-001..005) out of stock

    today = date.today()
    period_end = today
    period_start = today - timedelta(days=179)

    active_core_skus = [f"sku-0{i}" for i in range(19, 28)]  # 9 SKUs (paired prices average exact ₹500)
    newly_stocked_out_skus = [f"sku-0{i:02d}" for i in range(6, 19)]  # 13 SKUs

    # Schedule exact 130 orders (₹65,000) across the 13 newly stocked-out SKUs over 30 days
    # Paired prices: (600+400), (550+450), (650+350), plus 500s -> each pair = 1000/2 = ₹500 avg!
    prev_extra_pairs = [
        ("sku-006", "sku-007"),  # 600 + 400 = 1000
        ("sku-008", "sku-009"),  # 550 + 450 = 1000
        ("sku-010", "sku-011"),  # 650 + 350 = 1000
        ("sku-012", "sku-013"),  # 500 + 500 = 1000
        ("sku-014", "sku-015"),  # 500 + 500 = 1000
        ("sku-016", "sku-016"),  # 500 + 500 = 1000
        ("sku-017", "sku-018"),  # 550 + 450 = 1000
    ]

    performances = []
    for days_from_end in range(179, -1, -1):
        current_date = period_end - timedelta(days=days_from_end)
        in_this_month = days_from_end < 30
        in_last_month = 30 <= days_from_end < 60

        day_orders: dict[str, int] = {}
        day_cancellations: dict[str, int] = {}

        # Core 9 active SKUs always contribute 1 order/day = 9 orders/day = ₹4,500/day
        for pid in active_core_skus:
            day_orders[pid] = 1

        if not in_this_month:
            # In Last Month (days 30..59) and earlier months: add 130 orders (65 pairs) over 30 days
            # Cycle slot within 30-day block: 5 days get 3 pairs (6 orders), 25 days get 2 pairs (4 orders) -> 15 + 50 = 65 pairs = 130 orders!
            block_day = (days_from_end - 30) % 30
            pairs_today = 3 if block_day < 5 else 2
            for p_idx in range(pairs_today):
                a, b = prev_extra_pairs[(block_day * 3 + p_idx) % len(prev_extra_pairs)]
                day_orders[a] = day_orders.get(a, 0) + 1
                day_orders[b] = day_orders.get(b, 0) + 1

        # Exact cancellations:
        # This month (0..29): 38 total across 30 days -> 2 on days 0..7, 1 on days 8..29
        if in_this_month:
            cancels_today = 2 if days_from_end < 8 else 1
            for c_idx in range(cancels_today):
                target_pid = active_core_skus[(days_from_end + c_idx) % len(active_core_skus)]
                day_cancellations[target_pid] = day_cancellations.get(target_pid, 0) + 1
        elif in_last_month:
            # Last month (30..59): 32 total across 30 days -> 2 on days 30..31, 1 on days 32..59
            cancels_today = 2 if (days_from_end - 30) < 2 else 1
            for c_idx in range(cancels_today):
                target_pid = active_core_skus[(days_from_end + c_idx) % len(active_core_skus)]
                day_cancellations[target_pid] = day_cancellations.get(target_pid, 0) + 1
        else:
            # Earlier history: ~8% cancellation (1/day)
            target_pid = active_core_skus[days_from_end % len(active_core_skus)]
            day_cancellations[target_pid] = 1

        for p in products:
            pid = p.id
            orders = day_orders.get(pid, 0)
            units = orders  # 1 unit per order keeps ASP exact at ₹500
            net_sales = units * p.selling_price
            gross_sales = net_sales
            discounts = 0
            cancellations = day_cancellations.get(pid, 0)
            returns = 1 if (orders > 0 and (days_from_end + hash(pid)) % 35 == 0) else 0
            dispatched = max(0, orders - cancellations)

            is_stockout = (pid in [f"sku-0{i:02d}" for i in range(1, 6)]) or (
                in_this_month and pid in newly_stocked_out_skus
            )

            # Visibility / views: drop sharply when stocked out, lower visibility on remaining catalog
            if orders > 0:
                views = orders * (42 if in_this_month else 45)
                clicks = orders * 9
            elif pid == "sku-030" and in_this_month:
                # Slow/dead stock visibility signal
                views = 45
                clicks = 2
            else:
                views = 0
                clicks = 0

            conversion = (orders / views) if views > 0 else None

            performances.append(
                DailyPerformance(
                    seller_id=seller.id,
                    sku_id=pid,
                    perf_date=current_date,
                    units_sold=units,
                    gross_sales=gross_sales,
                    discounts=discounts,
                    net_sales=net_sales,
                    views=views,
                    clicks=clicks,
                    orders=orders,
                    conversion_rate=round(conversion, 4) if conversion is not None else None,
                    cancellations=cancellations,
                    returns=returns,
                    dispatched_units=dispatched,
                    stockout_indicator=is_stockout,
                    data_quality="mock",
                    source="snapdeal-demo-seeder",
                )
            )

    db.add_all(performances)
    db.commit()

    # ── Inventory snapshots (current) ─────────────────────────────────
    snapshots = []
    for p in products:
        snapshots.append(
            InventorySnapshot(
                sku_id=p.id,
                snapshot_at=datetime.utcnow(),
                available_qty=p.current_stock,
                received=0,
                sold=0,
                returned=0,
                adjusted=0,
                confirmed_incoming_qty=p.incoming_stock,
                expected_arrival=(today + timedelta(days=p.supplier_lead_time_days))
                if p.incoming_stock > 0
                else None,
            )
        )
    db.add_all(snapshots)
    db.commit()

    # ── Calendar events (Indian festivals with provenance) ────────────
    events = [
        CalendarEvent(
            event_name="Diwali Sale Window",
            event_type="festival",
            start_date=date(today.year, 10, 20),
            end_date=date(today.year, 10, 24),
            geography="India",
            shopping_lead_in_days=14,
            category_relevance='["Home & Kitchen", "Fashion", "Electronics", "Personal Care"]',
            source_url="https://example.com/diwali-calendar",
            verified_at=datetime.utcnow(),
            confidence="verified",
            year=today.year,
        ),
        CalendarEvent(
            event_name="Wedding & Festive Gifting Season",
            event_type="wedding",
            start_date=date(today.year, 11, 1),
            end_date=date(today.year, 12, 15),
            geography="Maharashtra",
            shopping_lead_in_days=10,
            category_relevance='["Fashion", "Home & Kitchen"]',
            source_url="https://example.com/wedding-season",
            verified_at=None,
            confidence="scenario",
            year=today.year,
        ),
        CalendarEvent(
            event_name="Upcoming Festival Mega Sale",
            event_type="festival",
            start_date=today + timedelta(days=14),
            end_date=today + timedelta(days=19),
            geography="India",
            shopping_lead_in_days=14,
            category_relevance='["Home & Kitchen", "Fashion", "Electronics", "Personal Care"]',
            source_url="https://example.com/upcoming-festival",
            verified_at=datetime.utcnow(),
            confidence="scenario",
            year=today.year,
        ),
    ]
    db.add_all(events)
    db.commit()

    # ── Actionable Draft Recommendations (require seller approval) ────
    recs = [
        Recommendation(
            id="rec-001",
            seller_id=seller.id,
            title="Restock 13 newly stocked-out fast-moving SKUs first",
            problem_or_opportunity=(
                "Out-of-stock products rose from 5 to 18 this month, directly driving the 32.5% drop "
                "in orders (400 → 270) and revenue (₹2,00,000 → ₹1,35,000) while ASP held steady at ₹500."
            ),
            evidence="13 SKUs (sku-006 to sku-018) contributed 130 orders (₹65,000) last month before hitting 0 stock.",
            suggested_action="Place priority replenishment POs for the top 6–8 fastest-moving stockout SKUs within your ₹40,000 budget.",
            expected_impact="Recover ~₹45,000–₹65,000/month in lost orders (accounting for 3–14 day supplier lead times).",
            cost_or_budget=_paise(36000),
            risk="low",
            confidence="high",
            urgency="high",
            priority=1,
            assumptions="Assumes supplier delivery within lead-time window and steady customer demand at ₹500 ASP.",
            what_to_measure_next="Daily order recovery and stockout count dropping from 18 toward ≤ 5.",
            requires_approval=True,
            approval_status="pending",
            execution_status="not_started",
            action_type="restock",
            outcome_status="pending",
        ),
        Recommendation(
            id="rec-002",
            seller_id=seller.id,
            title="Fix stock-sync & dispatch SLAs to cut cancellations from 14% to ≤ 8%",
            problem_or_opportunity=(
                "Cancellation rate jumped from 8% (32/400) to 14% (38/270), eroding net revenue and hurting marketplace search rank."
            ),
            evidence="38 cancelled orders this month; higher cancellation rate typically correlates with overselling low-stock SKUs or late dispatch.",
            suggested_action="Enable real-time inventory buffers (reserve 2–3 units) and audit 24-hour courier pickup SLAs.",
            expected_impact="Save ~16 orders/month (~₹8,000/month) and improve listing ranking score.",
            cost_or_budget=0,
            risk="low",
            confidence="medium",
            urgency="high",
            priority=2,
            assumptions="Assumes majority of cancellations are seller-side stockouts or dispatch delays rather than buyer COD refusals.",
            what_to_measure_next="Weekly cancellation rate dropping back below 8%.",
            requires_approval=True,
            approval_status="pending",
            execution_status="not_started",
            action_type="cancellation_fix",
            outcome_status="pending",
        ),
        Recommendation(
            id="rec-003",
            seller_id=seller.id,
            title="Boost visibility on in-stock ₹500 SKUs without cutting prices",
            problem_or_opportunity=(
                "ASP remained stable at ₹500, showing pricing is not the root cause—instead, 18 stockouts reduced overall catalog views by ~32%."
            ),
            evidence="Average selling price unchanged at ₹500; conversion rate on active listings remains ~2.4%, while total store impressions dropped.",
            suggested_action="Refresh titles/keywords on the 12 in-stock SKUs and allocate ₹4,000 to Snapdeal sponsored ads on high-margin items.",
            expected_impact="Recover 15–25% of lost impressions and lift active SKU orders without sacrificing margin.",
            cost_or_budget=_paise(4000),
            risk="medium",
            confidence="medium",
            urgency="medium",
            priority=3,
            assumptions="Assumes ad CPC stays within category norms and margin floor stays ≥ 25%.",
            what_to_measure_next="7-day impressions, CTR, and ad-attributed orders on active SKUs.",
            requires_approval=True,
            approval_status="pending",
            execution_status="not_started",
            action_type="visibility",
            outcome_status="pending",
        ),
        Recommendation(
            id="rec-hist-001",
            seller_id=seller.id,
            title="Pre-season restock on Cotton Bedsheets & Ethnic Kurtis (Last Quarter)",
            problem_or_opportunity="Previous stockout risk on top festival staples ahead of peak shopping window.",
            evidence="30-day run-rate showed 4+ units/day with 4–5 day supplier lead time.",
            suggested_action="Ordered 120 units ahead of peak window across fast-moving Home & Fashion SKUs.",
            expected_impact="Protected ~₹60,000 revenue during peak week.",
            cost_or_budget=_paise(38000),
            risk="low",
            confidence="high",
            urgency="medium",
            priority=4,
            assumptions="Based on observed 30-day velocity.",
            what_to_measure_next="Sell-through rate and realised gross margin.",
            requires_approval=True,
            approval_status="approved",
            execution_status="executed",
            action_type="restock",
            outcome_status="positive",
            actual_units_ordered=120,
            actual_revenue_delta_pct=28.5,
            actual_margin_pct=26.2,
            outcome_notes="Seller restocked 120 units cleanly; monthly sales increased +28.5% with 26.2% margin.",
            outcome_recorded_at=datetime.utcnow() - timedelta(days=20),
        ),
    ]
    db.add_all(recs)
    db.commit()

    print(
        f"Demo data seeded: {len(products)} SKUs, {len(performances)} daily records, "
        f"{len(events)} calendar events, {len(recs)} recommendations"
    )


def reset_demo_data() -> None:
    """Drop and recreate all tables, then seed demo data."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        create_demo_data(db)
    finally:
        db.close()
