# 02 — Product Requirements and Seller Data Model

## Goal

Define the seller-facing product behaviour and a realistic, internally consistent data model before implementing business logic.

## Product behaviour

The Virtual KAM must answer questions such as:
- Why did my sales fall this month?
- Which products are losing sales because they are out of stock?
- Which SKUs should I replenish before the next relevant festival?
- What is driving cancellations?
- Which products deserve a price or listing review?
- What should I focus on today, given my budget and business goals?

It should distinguish facts from hypotheses. If the data cannot establish a cause, say what additional data is needed.

## Required entities

Adapt naming to the existing ORM and conventions. At minimum model:

### Seller
- id, display_name, marketplace, business_category
- state, city, serviceable_regions, timezone
- business_goals, target_growth, target_margin
- available_replenishment_budget
- risk_tolerance (`low`, `medium`, `high`)
- preferred_stock_cover_days
- storage_capacity (optional)
- created_at, updated_at

### Product / SKU
- id, seller_id, sku_code, title, category, subcategory
- selling_price, unit_cost, minimum_margin
- current_stock, reserved_stock, incoming_stock
- supplier_lead_time_days, minimum_order_quantity
- region relevance, seasonality tags
- active/listing status

### Daily SKU performance
- date, seller_id, sku_id
- units_sold, gross_sales, discounts, net_sales
- views/impressions, clicks, orders, conversion rate (nullable)
- cancellations, returns, dispatched units
- stockout indicator or available-stock history
- source and data-quality status

### Inventory snapshots and movements
- timestamp/date, sku_id, available quantity
- received, sold, returned, adjusted quantities
- confirmed incoming quantity and expected arrival date

### Orders (mock data only unless a real integration is later authorised)
- order id, sku id, order date, status, cancellation reason, dispatch delay, region

### Calendar events
- event name, event type, start/end date, geography/state relevance
- shopping lead-in window, category relevance
- source URL/name, verified_at, confidence/status
- year and date convention where relevant

### Recommendation
- id, seller_id, created_at, status
- title, problem/opportunity, evidence, suggested action
- expected impact range, cost, risk, confidence, priority
- assumptions, expiry, related SKU IDs
- approval status and execution status

### Conversation
- session id, seller id, timestamps
- transcript turns, tool-call metadata, summary and consent/retention settings
- Avoid storing raw audio by default.

## Data quality requirements

- Store currency as integer paise or a documented decimal type; display INR.
- Store dates with explicit timezone rules. Use ISO dates in APIs.
- Avoid mixing order count, unit count and revenue.
- Handle missing values as missing—not zero.
- Validate that seller IDs and SKU IDs are correctly related.
- Prevent duplicate daily SKU records.
- Preserve source/provenance and whether values are mock, observed or derived.
- Do not infer demand from sales during stockout periods without marking the estimate. Sales are censored when inventory was unavailable.

## Demo dataset

Create deterministic, reproducible mock data for at least:
- One Indian marketplace seller.
- 10–20 SKUs across 2–4 categories.
- 6–12 months of daily or weekly performance.
- Inventory snapshots, lead times, cost and price.
- Several cancellation and return reasons.
- Region and festival/event tags.
- A few deliberately planted business issues (e.g. stockout-linked lost sales, rising cancellations, falling conversion, dead stock).

Do not make every SKU show the same pattern. Include enough variation to test explanations.

The assignment's sample headline figures may be used as one demo scenario:
- Last month sales: ₹2,00,000; this month: ₹1,35,000.
- Orders: 400 → 270.
- Cancellation rate: 8% → 14%.
- Average selling price: ₹500 unchanged.
- Out-of-stock products: 5 → 18.

If using these figures, make the SKU-level data reconcile to them or clearly label them as a separate summary scenario. Do not present inconsistent totals as one dataset.

## API/data contracts

Define typed schemas for:
- Seller profile.
- Dashboard summary.
- SKU performance.
- Inventory health.
- Forecast output with prediction intervals.
- Diagnosis evidence.
- Recommendation and approval state.
- Conversation turn and voice-session state.

## Acceptance criteria

- [ ] Data model is documented and implemented using the repository's conventions.
- [ ] Demo data is deterministic and reproducible.
- [ ] Headline totals reconcile with underlying records, or are explicitly separated.
- [ ] Missing and stockout-censored data are handled explicitly.
- [ ] Indian geography, currency and timezone are represented.
- [ ] API schemas identify provenance and data status.
