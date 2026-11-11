# 12 — Final Acceptance and Handoff

## Goal

Perform a final product, code, security and demo review. Do not add major new features during this stage; fix defects and document remaining gaps.

## Final functional checklist

### Product and UI
- [ ] Seller can view dashboard KPIs and trends.
- [ ] Seller can inspect SKU and inventory health.
- [ ] Recommendations show evidence, impact, risk and confidence.
- [ ] Seller settings influence recommendations.
- [ ] UI distinguishes observed, calculated, forecast and simulated data.

### Intelligence
- [ ] KPI calculations are deterministic and tested.
- [ ] Diagnosis avoids unsupported causal claims.
- [ ] Forecast is evaluated against a baseline.
- [ ] Festival dates have provenance and regional relevance.
- [ ] Festival uplift is evidence-based or explicitly a scenario assumption.
- [ ] Replenishment considers lead time, current stock, incoming stock and budget.

### Agent
- [ ] Agent uses tools for current seller facts.
- [ ] Agent shares the same business logic for text and voice.
- [ ] Agent explains evidence and uncertainty.
- [ ] Agent does not invent competitor data or claim unexecuted actions.
- [ ] High-impact actions require approval.

### Voice
- [ ] Browser microphone permission and session start/stop work.
- [ ] STT transcript is visible.
- [ ] Local Ollama generates the response.
- [ ] TTS audio is played and response text is visible.
- [ ] Turn-taking and supported interruption work.
- [ ] Text fallback works.
- [ ] Provider/network failures are handled.
- [ ] Data locality is accurately documented.

### Engineering
- [ ] Tests, lint and type checks have been run where configured.
- [ ] No secrets are committed.
- [ ] No unverified APIs remain without a documented caveat.
- [ ] Database setup/migrations are reproducible.
- [ ] README run instructions are accurate.
- [ ] No temporary debug code or misleading demo labels remain.

## Demo recording script (about 1–2 minutes)

1. Open the seller dashboard and point out the revenue/order change.
2. Start the voice assistant and ask: “Why are my sales down this month?”
3. Let it explain the strongest evidence, such as order decline, stockouts and cancellation changes, only if those facts are present in the dataset.
4. Ask: “Which products should I prepare for the next relevant festival?”
5. Show how it checks the seller's region, category, historical demand, forecast, stock and supplier lead time.
6. Show a replenishment recommendation with uncertainty, budget and assumptions.
7. Ask it to prepare the action; show that seller approval is required.
8. End the session and show the transcript/recommendation record.

## Required handoff report

Create `docs/FINAL_HANDOFF.md` with:
- Product features implemented.
- Architecture diagram or text-based component map.
- Models and providers selected, with versions.
- What runs locally and what uses external services.
- Environment variables required (names only; no secret values).
- Exact install, setup, run and test commands.
- Database setup and demo-data reset instructions.
- Voice setup and troubleshooting.
- Actual test results and measured voice latency.
- Known bugs, limitations and unimplemented features.
- Files created/modified.
- Steps needed to connect a real marketplace API in the future.
- Confirmation that no Snapdeal integration was claimed unless it actually exists.

## Final response to the project owner

Summarise:
1. What is working.
2. Which files changed.
3. Which LLM, STT, TTS, transport and forecasting method were selected.
4. Whether audio or conversation data leaves the machine.
5. Required accounts/API keys, if any.
6. Exact commands to run the app.
7. Tests actually executed and their results.
8. Remaining assumptions or decisions requiring confirmation.

Do not claim full completion if any acceptance criterion is unmet. Mark each unmet item clearly.
