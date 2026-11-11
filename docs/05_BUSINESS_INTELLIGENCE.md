# 05 — Business Intelligence, Diagnosis and Recommendations

## Goal

Make the Virtual KAM capable of explaining what is happening in a seller's business using evidence—not generic LLM advice.

## Core KPI calculations

Implement deterministic functions for:
- Gross sales and net sales (define treatment of discounts, cancellations and returns).
- Orders and units sold.
- Average selling price (state numerator and denominator).
- Cancellation rate (define denominator consistently).
- Return rate (define denominator consistently).
- Conversion rate when views/clicks and orders are available.
- Stockout SKU count.
- Inventory value at cost and at selling price (label clearly).
- Days of stock cover.
- SKU/category contribution to revenue and change.
- Period-over-period absolute and percentage change.

Every KPI must include:
- Formula/definition.
- Period and comparison period.
- Source fields.
- Missing-data behaviour.
- Unit and currency.
- Calculation timestamp.

## Diagnosis engine

Build a rule-based diagnosis layer before relying on LLM interpretation. Examples:
- Revenue down + orders down + ASP stable → order volume is a major contributor; investigate traffic, conversion and availability.
- Out-of-stock SKUs increased + those SKUs historically contribute material sales → stock availability is a plausible contributor.
- Cancellation rate increased → segment by cancellation reason, dispatch delay, SKU and region.
- Views stable + conversion down → investigate price, listing quality, reviews, delivery promise and stock availability if those data exist.
- High stock + low recent sales + weak forecast → possible dead-stock exposure.
- High sales growth + low stock cover + long supplier lead time → replenishment risk.

Do not state causation from correlation. Use wording such as “is contributing”, “is associated with” or “is a likely driver” only when the data supports it. Otherwise say “possible cause” and specify the missing evidence.

## Recommendation format

Every recommendation should contain:
- `title`
- `problem_or_opportunity`
- `evidence`: metrics, periods and affected SKUs
- `suggested_action`
- `expected_impact`: range or qualitative estimate, never false precision
- `cost_or_budget`
- `risk`
- `confidence`
- `urgency`
- `assumptions`
- `what_to_measure_next`
- `requires_approval`

Prioritise recommendations using transparent factors such as impact, urgency, confidence, cost and feasibility. Expose the reason for priority.

## Seller-specific decision profile

Use:
- Available cash/budget.
- Risk tolerance.
- Target gross margin.
- Growth target.
- Preferred stock-cover days.
- Supplier lead time.
- Storage capacity.
- Category and region.
- Seller's explicit goals.

Two sellers with identical sales can require different actions because their budgets and risk tolerance differ.

## LLM boundary

The LLM may:
- Explain computed findings in natural language.
- Ask for missing context.
- Compare available options using supplied calculations.
- Summarise recommendations.

The LLM must not:
- Invent KPIs or source data.
- Pretend to have checked live competitor prices.
- Manufacture festival demand uplift.
- Claim that an action was executed when it was only suggested.
- Override margin, budget or safety constraints.

## Acceptance criteria

- [ ] KPI functions have unit tests and documented formulas.
- [ ] Diagnoses cite the exact metrics and periods used.
- [ ] Recommendations are structured, prioritised and seller-aware.
- [ ] Causal language is calibrated to evidence.
- [ ] Unknown or missing data produces a clear limitation.
- [ ] The same input data produces the same deterministic calculations.
