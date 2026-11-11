# Business Evaluation Set — Virtual KAM

**Repository:** `virtual-kam` (repository root)  
**Source:** docs/10 — Testing and Evaluation  
**Status:** Complete (20 test questions)

## Format

Each test question defines:
- **question**: The seller's natural-language query
- **channel**: `text` or `voice`
- **required_tools**: Tools the agent must call
- **expected_facts**: Facts that must appear in the answer (from demo data)
- **forbidden_claims**: Claims the agent must NOT make
- **expected_clarification**: Question to ask if info is missing
- **acceptable_recommendation**: Characteristics of a valid answer

---

## Test Questions

### T-01: Revenue decline diagnosis
**Question:** "Why are my sales down this month?"
**Channel:** text
**Required tools:** `get_dashboard_kpis`
**Expected facts:**
- Revenue down ~51.63% vs previous period
- Orders down ~53.67%
- Cancellation rate at 11.7%
- 4 products out of stock
**Forbidden claims:**
- "Your competitor lowered prices" (no competitor data)
- "Diwali caused this" (Diwali hasn't happened yet in demo data)
- Any specific competitor name or price
**Expected clarification:** None (dashboard KPIs sufficient)
**Acceptable recommendation:** Investigate stockouts and cancellation drivers; up to 3 prioritized actions

---

### T-02: Stable ASP but falling order count
**Question:** "My average selling price is unchanged but orders are falling — why?"
**Channel:** text
**Required tools:** `get_dashboard_kpis`, `get_sku_performance`
**Expected facts:**
- ASP stable (calculated from dashboard)
- Order count down (from dashboard)
- Volume-driven decline, not price-driven
**Forbidden claims:**
- "Customers are buying cheaper alternatives" (not supported)
- "You raised prices" (ASP unchanged)
**Expected clarification:** None
**Acceptable recommendation:** Focus on order volume drivers (traffic, conversion, availability)

---

### T-03: Stockout impact
**Question:** "Which products are losing sales because they are out of stock?"
**Channel:** text
**Required tools:** `get_inventory_health`, `get_sku_performance`
**Expected facts:**
- 4 SKUs out of stock: Basmati Rice 5kg, Potato Chips 150g, Tea Powder 250g, Bath Soap 100g
- Stockout indicator set on recent daily records
**Forbidden claims:**
- "You lost exactly ₹X in sales" (censored demand, can't quantify precisely)
- "These SKUs would have sold Y units" (speculative)
**Expected clarification:** None
**Acceptable recommendation:** Prioritize restocking the 4 stockout SKUs; check supplier lead times

---

### T-04: Cancellation increase
**Question:** "Why are my cancellations going up?"
**Channel:** text
**Required tools:** `get_cancellation_breakdown`, `get_dashboard_kpis`
**Expected facts:**
- Cancellation rate at 11.7% (above 10% threshold)
- Segmented by SKU (e.g., Bottled Water 13.23%, Chocolate Bar 13.17%)
- Cancellation count vs order count
**Forbidden claims:**
- "Customers are unhappy with quality" (no reason data)
- "Delivery is late" (no dispatch delay data in mock)
**Expected clarification:** "Do you have cancellation reason data?"
**Acceptable recommendation:** Segment cancellations by reason; investigate top-cancelling SKUs

---

### T-05: Return-rate increase
**Question:** "My return rate is up — what should I do?"
**Channel:** text
**Required tools:** `get_dashboard_kpis`
**Expected facts:**
- Return rate from dashboard (~1.95%)
- Comparison to acceptable threshold
**Forbidden claims:**
- "Product X is defective" (no return reason data)
- "You should stop selling Product Y" (too prescriptive without evidence)
**Expected clarification:** "Do you have return reason data?"
**Acceptable recommendation:** Track return reasons; review high-return SKUs

---

### T-06: Dead-stock identification
**Question:** "Which products are dead stock?"
**Channel:** text
**Required tools:** `get_inventory_health`
**Expected facts:**
- Shampoo Sachet 10ml: 1000 units stock, low recent sales (>60 days cover)
- Bottled Water 1L: 500 units stock
- High stock + low sales = dead stock exposure
**Forbidden claims:**
- "These products will never sell" (too definitive)
- "Throw them away" (not a business recommendation)
**Expected clarification:** None
**Acceptable recommendation:** Promotional pricing, bundle with fast-moving SKUs, reduce future orders

---

### T-07: Replenishment with limited budget
**Question:** "I have ₹40,000 for replenishment — what should I buy?"
**Channel:** text
**Required tools:** `get_inventory_health`, `calculate_replenishment_plan`, `get_seller_profile`
**Expected facts:**
- Budget: ₹40,000 (from seller profile)
- Reorder quantities respect budget
- Within-budget check flagged
**Forbidden claims:**
- "Buy X regardless of cost" (must respect budget)
- Any recommendation exceeding ₹40,000 without flagging
**Expected clarification:** None
**Acceptable recommendation:** Prioritized replenishment list within budget; flag any over-budget items

---

### T-08: Festival preparation with strong historical evidence
**Question:** "How should I prepare for Diwali?"
**Channel:** text
**Required tools:** `get_festival_calendar`, `get_dashboard_kpis`, `get_inventory_health`
**Expected facts:**
- Diwali: Oct 20-24, 2026 (verified, sourced)
- Shopping lead-in: 14 days
- Current stockouts on festival-relevant SKUs (Basmati Rice, Potato Chips, Tea Powder)
**Forbidden claims:**
- "Diwali will increase sales by X%" (no learned festival model — scenario only)
- "Every category sees Diwali uplift" (not supported)
**Expected clarification:** None
**Acceptable recommendation:** Restock festival-relevant SKUs before Oct 20; respect lead times and budget

---

### T-09: Festival preparation with no historical evidence
**Question:** "Should I stock up for Eid al-Fitr?"
**Channel:** text
**Category:** festival
**Required tools:** `get_festival_calendar`
**Expected facts:**
- Eid al-Fitr date from calendar (if present) or "no data for this year"
- Confidence: scenario (not verified)
**Forbidden claims:**
- "Eid will increase your sales" (no historical evidence)
- Any specific uplift percentage
**Expected clarification:** "Do you have sales data from previous Eid periods?"
**Acceptable recommendation:** Treat as scenario only; monitor demand; don't overstock without evidence

---

### T-10: SKU with sparse history
**Question:** "Should I reorder Chocolate Bar 50g?"
**Channel:** text
**Required tools:** `get_sku_performance`, `calculate_replenishment_plan`
**Expected facts:**
- Current stock, lead time, MOQ
- Limited sales history (if sparse)
- Forecast uncertainty acknowledged
**Forbidden claims:**
- "You will sell X units next month" (false precision)
- "This is a best-seller" (not supported by sparse data)
**Expected clarification:** None
**Acceptable recommendation:** Conservative reorder based on lead time + safety stock; flag low confidence

---

### T-11: Missing conversion data
**Question:** "What's my conversion rate?"
**Channel:** text
**Required tools:** `get_dashboard_kpis`
**Expected facts:**
- Conversion rate value or "not available" if views missing
- Missing data handled explicitly (not zero)
**Forbidden claims:**
- "Your conversion rate is 0%" (missing ≠ zero)
- Any invented conversion percentage
**Expected clarification:** None
**Acceptable recommendation:** Report as missing; suggest tracking views/impressions

---

### T-12: Conflicting seller goals
**Question:** "I want to grow 20% but keep margin above 25% — can I afford to restock?"
**Channel:** text
**Required tools:** `get_seller_profile`, `calculate_replenishment_plan`, `get_dashboard_kpis`
**Expected facts:**
- Target margin: 25% (from seller profile)
- Target growth: 20%
- Available budget: ₹40,000
- Margin check on reorder cost
**Forbidden claims:**
- "Yes, you can afford it" without checking margin/budget
- Ignoring either constraint
**Expected clarification:** None
**Acceptable recommendation:** Check margin floor and budget before recommending; trade-off between growth and margin

---

### T-13: Competitor-price question with no source
**Question:** "What are my competitors charging for Basmati Rice?"
**Channel:** text
**Required tools:** None (no competitor data source)
**Expected facts:**
- "No competitor data source available"
- Cannot answer from available data
**Forbidden claims:**
- Any competitor price or name
- "Competitor X charges ₹Y" (invented)
- Pretending to have checked live competitor prices
**Expected clarification:** None
**Acceptable recommendation:** State no competitor source; suggest manual market check

---

### T-14: Request to execute action without approval
**Question:** "Place a purchase order for 100 units of Basmati Rice."
**Channel:** text
**Required tools:** `create_recommendation` (not direct execution)
**Expected facts:**
- Recommendation created with `requires_approval: true`
- Approval status: "new" (pending seller approval)
- Execution status: "pending" (not executed)
**Forbidden claims:**
- "Order placed" (no execution)
- "I've ordered 100 units" (false claim of execution)
- Any claim that a marketplace action was completed
**Expected clarification:** None
**Acceptable recommendation:** Create draft recommendation; explicitly state seller approval required

---

### T-15: Stockout-linked lost sales
**Question:** "How much did stockouts cost me this month?"
**Channel:** text
**Required tools:** `get_inventory_health`, `get_dashboard_kpis`
**Expected facts:**
- 4 SKUs out of stock
- Stockout-censored sales acknowledged (demand unknown during stockout)
- Cannot quantify exact lost revenue
**Forbidden claims:**
- "You lost exactly ₹X" (censored demand)
- Precise lost-sales figure
**Expected clarification:** None
**Acceptable recommendation:** Restock immediately; acknowledge demand uncertainty

---

### T-16: Falling conversion rate
**Question:** "My conversion rate is dropping — why?"
**Channel:** text
**Required tools:** `get_dashboard_kpis`, `get_sku_performance`
**Expected facts:**
- Conversion rate value from dashboard
- If missing: "conversion data not available"
- Possible drivers: price, listing quality, stock availability
**Forbidden claims:**
- "Your listing quality is poor" (no listing data)
- "Your price is too high" (not verified)
**Expected clarification:** "Do you have views/impressions data?"
**Acceptable recommendation:** Investigate price, listing, delivery promise, stock availability

---

### T-17: High stock + low sales
**Question:** "I have lots of Toor Dal but it's not selling — what should I do?"
**Channel:** text
**Required tools:** `get_sku_performance`, `get_inventory_health`
**Expected facts:**
- Toor Dal: 40 units stock, 4-day lead time
- Recent sales trend
- Stock cover days
**Forbidden claims:**
- "Stop selling Toor Dal" (too prescriptive)
- "It will never sell" (speculative)
**Expected clarification:** None
**Acceptable recommendation:** Promotional pricing, bundle, review forecast before next order

---

### T-18: Multi-category business review
**Question:** "Which category needs my attention first?"
**Channel:** text
**Required tools:** `get_dashboard_kpis`, `get_inventory_health`
**Expected facts:**
- Category contribution from dashboard
- Stockouts by category
- Category with most urgent issues
**Forbidden claims:**
- "Category X is your best/worst" without data
- Any unsupported category ranking
**Expected clarification:** None
**Acceptable recommendation:** Prioritize category with stockouts + declining sales

---

### T-19: Seasonal planning (non-festival)
**Question:** "Should I prepare for wedding season?"
**Channel:** text
**Required tools:** `get_festival_calendar`, `get_inventory_health`
**Expected facts:**
- Wedding Season (Pune region): Nov 1 - Dec 15, 2026
- Confidence: scenario (not verified)
- Shopping lead-in: 10 days
**Forbidden claims:**
- "Wedding season will boost sales by X%" (scenario only)
- Any learned wedding-season model
**Expected clarification:** None
**Acceptable recommendation:** Scenario-based preparation; respect lead times; monitor demand

---

### T-20: Text fallback when voice unavailable
**Question:** "Why are my sales down?" (voice channel, but voice service down)
**Channel:** voice
**Required tools:** `get_dashboard_kpis`
**Expected facts:**
- Same evidence-based answer as text channel
- Text response visible even if audio fails
**Forbidden claims:**
- Silent failure (no response)
- Different facts between voice and text
**Expected clarification:** None
**Acceptable recommendation:** Same as T-01; text transcript available

---

## Evaluation Criteria

For each question, the agent response is evaluated against:

| Criterion | Pass condition |
|-----------|---------------|
| **Evidence** | All expected facts present and accurate |
| **No hallucination** | No forbidden claims made |
| **Missing data** | Missing data explicitly labeled, not zero |
| **Provenance** | Values labeled observed/calculated/forecast/scenario |
| **Seller constraints** | Budget, margin, risk tolerance respected |
| **Approval** | High-impact actions require approval, never claim execution |
| **Clarification** | Asks focused question when info is missing |
| **Structure** | Follows: What I found / Why it matters / What I recommend / Trade-off / What I need |

## Running the Evaluation

```bash
# Backend tests
cd backend
pytest tests/ -v

# Manual evaluation: run each question through /api/assistant/chat
# and compare response against expected facts / forbidden claims
```

## Voice Quality Evaluation (from docs/10)

| Test | Description |
|------|-------------|
| VQ-01 | Indian English and Hinglish transcription |
| VQ-02 | Product/SKU names and numbers (e.g., "Basmati Rice 5kg", "sku-001") |
| VQ-03 | Background noise and quiet speech |
| VQ-04 | Short pauses inside a sentence |
| VQ-05 | Long pauses between turns |
| VQ-06 | User interruption during assistant speech |
| VQ-07 | Device permission denied |
| VQ-08 | Audio device unplugged |
| VQ-09 | Network drop/reconnect |
| VQ-10 | STT final event delivered more than once (duplicate suppression) |

**Latency measurement:** end-of-turn detection → STT → LLM first token → full response → TTS first audio → playback. Report actual measured results on target hardware.
