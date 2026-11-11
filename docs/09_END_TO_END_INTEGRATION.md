# 09 — End-to-End Integration

## Goal

Connect the frontend, backend, business intelligence, forecasting, KAM agent and Pipecat voice service into one coherent application.

## Integration sequence

1. Load authenticated seller context.
2. Fetch dashboard and SKU data.
3. Run KPI calculations and diagnosis.
4. Generate or retrieve forecasts.
5. Build prioritised recommendations.
6. Make the same trusted tools available to the KAM agent.
7. Connect the voice session to the same agent service used by text chat.
8. Render transcripts, responses, evidence and recommendations in the UI.
9. Persist recommendation decisions and concise conversation summaries.

## Shared assistant service

Text and voice must use the same business-agent logic. Do not create one set of business rules for text and another for voice.

Create a channel-neutral input contract such as:
- seller/session context
- user message/transcript
- channel (`text` or `voice`)
- conversation ID
- optional locale/language metadata

Return:
- response text
- structured findings
- recommendation references
- follow-up question if needed
- tool activity summary suitable for UI
- safe speech text (concise, no markdown-heavy formatting)

## Voice response design

The agent may produce a detailed visual answer and a concise spoken answer. Keep them semantically consistent. Do not let the spoken response introduce claims absent from the visual response.

## Failure handling

- If forecasting is unavailable, agent can still use current KPIs and explain the limitation.
- If voice is unavailable, text chat remains usable.
- If Ollama is unavailable, show a clear error; do not silently route to a hosted LLM.
- If data is stale, show its last updated timestamp.
- If a tool fails, agent should say it could not verify that information.

## End-to-end demo scenario

Create a reproducible demo:
1. Seller opens the dashboard.
2. App highlights revenue and order decline.
3. Seller asks by voice: “Why are my sales down this month?”
4. Agent retrieves period KPIs, SKU availability and cancellation breakdown.
5. Agent explains the largest supported drivers and names missing evidence.
6. Seller asks: “What should I restock before Diwali?”
7. Agent checks relevant festival calendar, SKU history, forecast, stock, supplier lead time and budget.
8. Agent presents a prioritised replenishment plan with uncertainty and assumptions.
9. Seller asks to prepare the plan; system creates a draft recommendation requiring approval.
10. Seller can review the plan in the UI.

Use the festival name as an example scenario, not a claim that every product experiences a Diwali uplift.

## Acceptance criteria

- [ ] Text and voice share the same agent and tools.
- [ ] Dashboard and recommendations use the same source of truth.
- [ ] Agent answers include evidence and timestamps.
- [ ] Voice transcript and spoken response match the agent output.
- [ ] Partial service failure degrades gracefully.
- [ ] Demo scenario can be repeated using deterministic data.
