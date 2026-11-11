# 00 — Master Instructions for the Virtual KAM Build

## Role

Act as a senior full-stack engineer, applied ML engineer, product designer and real-time voice engineer. Build the application in the existing repository. Work in small, reviewable stages and do not skip repository inspection.

## Product objective

Build a browser-based **AI-powered Virtual Key Account Manager (Virtual KAM)** for Indian marketplace sellers. It should help a seller understand the health of their shop, identify the causes of business changes, discover opportunities, forecast demand, plan inventory and discuss decisions through a natural voice conversation.

The assistant should behave like a commercially thoughtful business partner, not a generic chatbot. It should:
- Understand the seller's goals, product catalogue, operating constraints and business history.
- Proactively identify meaningful changes and opportunities.
- Explain the evidence behind each diagnosis.
- Recommend practical next steps with expected impact, cost, risk and confidence.
- Ask focused follow-up questions when required information is missing.
- Prepare actions for seller approval; never claim to have executed an action that the prototype cannot execute.
- Maintain conversational context across a voice session and, where configured, across sessions.

## Product modules

1. **Overview:** revenue, orders, units, average selling price, conversion, cancellation, return and inventory health.
2. **Sales intelligence:** trend changes, SKU/category contribution, regional and channel breakdowns.
3. **Inventory intelligence:** stock cover, stockout risk, dead stock, reorder quantity and supplier lead time.
4. **Pricing intelligence:** price history, margin floor, discount scenarios and competitor data only when supplied by a verified source.
5. **Fulfilment intelligence:** cancellation, dispatch delay, return and fulfilment signals.
6. **Visibility and conversion:** impressions/views, clicks, conversion funnel and listing-quality signals when data exists.
7. **Indian seasonality:** festival and regional shopping periods, wedding season and category-specific demand windows.
8. **Recommendations:** prioritised actions with rationale, assumptions, impact range, effort, urgency and confidence.
9. **KAM voice workspace:** real-time two-way spoken conversation with visible transcript and text fallback.
10. **Seller settings:** location/region, category, budget, risk appetite, target margin, supplier lead time, storage capacity and business goals.

## Global architecture rules

- Treat the LLM as the dialogue, reasoning and tool-orchestration layer—not as the database, calculator or forecasting model.
- Compute KPIs and business rules in deterministic code.
- Keep forecasting, anomaly detection, optimisation and agent orchestration in separate services.
- Make STT, LLM, TTS and audio transport replaceable through interfaces.
- Keep provider credentials and private endpoints on the server.
- Use typed request/response schemas and validate all external inputs.
- Do not invent seller data, competitor prices, festival dates, model performance or completed actions.
- Clearly label `observed`, `calculated`, `estimated`, `forecast` and `simulated` information.
- Use mock data for the prototype; do not imply a live Snapdeal integration. No Snapdeal API access is assumed.
- Keep an audit trail of recommendations and approved actions.
- Add human approval for price changes, purchasing, budget commitments, stock updates or other consequential actions.

## Required development behaviour

Before each stage:
1. Read the relevant stage file completely.
2. Inspect the existing code and identify reusable components.
3. State assumptions and the files likely to change.
4. Ask a question only if a missing decision blocks safe implementation. Otherwise choose a conservative default and document it.
5. Implement only the stage scope.

After each stage:
1. Run the relevant tests, lint and type checks that are available.
2. Report exact commands and actual outcomes. Never claim a test passed if it was not run.
3. List created/modified files.
4. List known limitations and next-stage dependencies.
5. Confirm each acceptance criterion explicitly.

## Definition of a successful first release

A seller can open the web app, inspect a realistic demo shop, ask the Virtual KAM questions by voice or text, receive evidence-based diagnoses and recommendations, hear spoken answers, interrupt the assistant where supported, and review the resulting actions and assumptions. The system remains useful if voice services are unavailable because text interaction remains available.

## First action

Execute Stage 01 only. Do not start building the whole product before the repository audit is complete.
