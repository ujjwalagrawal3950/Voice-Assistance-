# Architecture — Virtual KAM

**Repository:** `virtual-kam` (repository root)  
**Status:** Proposal  
**Topology:** Local demo (single machine) by default; split-network and hosted profiles documented.

## 1. Verified starting point (repository audit)

- Repository is effectively empty: only `main.py` (`print('hello world')`) and `docs/` (13 stage briefs).
- Python 3.15.0, pip 26.2.1, no virtual environment, no other packages installed.
- Not a git repository.
- No existing framework, database, frontend, or voice code. This is a greenfield build.

## 2. Target architecture (modular monolith)

Per docs 04 and start.md: a modular monolith is acceptable for the prototype. No microservices without a concrete deployment/scaling reason. Clear internal module boundaries with typed contracts.

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (React + TypeScript + Vite + Tailwind + shadcn/ui) │
│  ┌─────────────┐  ┌─────────────────────────────────────┐  │
│  │ Dashboard   │  │ KAM Workspace (voice + text chat)   │  │
│  │ SKU view    │  │ Recommendations + approvals         │  │
│  │ Settings    │  │ Text fallback (always available)    │  │
│  └──────┬──────┘  └──────────────┬────────────────────┘  │
│         │ HTTPS fetch            │ WebRTC / WebSocket    │
└─────────┼────────────────────────┼───────────────────────┘
          │                        │
          ▼                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Backend: FastAPI (Python 3.15) — modular monolith          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Seller &     │  │ Analytics /  │  │ Forecasting  │     │
│  │ Catalogue API│  │ KPI service  │  │ service      │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────┴───────┐     │
│  │ Recommend-   │  │ KAM Agent    │  │ Voice session│     │
│  │ ation service│  │ service      │  │ (Pipecat)    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         └─────────────────┴─────────────────┘             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Persistence & audit (SQLite, explicit migrations)  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  External (server-side only, never exposed to browser):     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │ Ollama   │  │ faster-  │  │ Piper    │                 │
│  │ (LLM)    │  │ whisper  │  │ (TTS)    │                 │
│  │ :11434   │  │ (STT)    │  │          │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### Service boundaries (7 modules, one application)

1. **Seller & catalogue service** — seller profile, products/SKUs, catalogue CRUD.
2. **Analytics / KPI service** — deterministic KPI calculations, period-over-period, contribution.
3. **Forecasting service** — SKU demand forecast, replenishment calculation, festival-aware.
4. **Recommendation service** — prioritised recommendations, approval state, audit trail.
5. **KAM agent service** — tool-using agent, text chat, shared with voice channel.
6. **Voice session service** — Pipecat pipeline, session bootstrap, transport.
7. **Persistence & audit service** — SQLite schema, migrations, conversation summaries, recommendation history.

## 3. Data model (summary; full schema in Stage 02)

| Entity | Key fields |
|--------|-----------|
| Seller | id, display_name, marketplace, business_category, state, city, timezone, business_goals, target_growth, target_margin, available_replenishment_budget, risk_tolerance, preferred_stock_cover_days, storage_capacity |
| Product/SKU | id, seller_id, sku_code, title, category, subcategory, selling_price (paise), unit_cost (paise), minimum_margin, current_stock, reserved_stock, incoming_stock, supplier_lead_time_days, minimum_order_quantity, seasonality_tags |
| Daily SKU performance | date, seller_id, sku_id, units_sold, gross_sales, discounts, net_sales, views, clicks, orders, conversion_rate, cancellations, returns, dispatched_units, stockout_indicator, data_quality |
| Inventory snapshot | timestamp, sku_id, available_qty, received, sold, returned, adjusted, confirmed_incoming_qty, expected_arrival |
| Calendar event | event_name, event_type, start_date, end_date, geography, shopping_lead_in, category_relevance, source_url, verified_at, confidence |
| Recommendation | id, seller_id, title, problem, evidence, suggested_action, expected_impact, cost, risk, confidence, urgency, assumptions, expiry, related_sku_ids, approval_status, execution_status |
| Conversation | session_id, seller_id, timestamps, transcript_turns, tool_call_metadata, summary, consent/retention |

**Currency:** integer paise, displayed as INR. **Dates:** ISO 8601 in APIs, explicit timezone rules. **Missing data:** represented as missing, not zero. **Stockout-censored sales:** flagged, not used as demand without labelling.

## 4. AI / agent responsibilities

- **LLM (Ollama, local only):** natural-language understanding, investigation planning, tool selection, explanation, conversation. Never calculates KPIs, never invents data, never claims unexecuted actions.
- **Tools (typed, seller-scoped):** `get_seller_profile`, `get_dashboard_kpis`, `get_sales_trend`, `get_sku_performance`, `get_inventory_health`, `get_cancellation_breakdown`, `get_conversion_funnel`, `get_forecast`, `get_festival_calendar`, `calculate_replenishment_plan`, `create_recommendation`, `get_recommendation_history`, `request_action_approval`.
- **Orchestration:** Explicit Python service/tool orchestration for MVP. LangGraph considered only if persistent state, branching, retries, or human-approval checkpoints justify it.
- **Autonomy levels:** Advisory (MVP) → Copilot (prepare action, seller approves). Never bounded automation without real integration.

## 5. Voice pipeline and deployment topology

**Pipeline:** Browser mic → audio transport → Pipecat → STT (faster-whisper) → Virtual KAM agent / Ollama → TTS (Piper) → audio transport → browser speaker.

**Transport:** To be verified against installed Pipecat version in Stage 08. Preferred: Pipecat-supported WebRTC transport. WebSocket only if genuinely appropriate for streaming + interruption. Do not assume `localhost` equivalence across browser, Docker container, and backend.

**Session scoping:** Frontend obtains scoped session token from `POST /api/voice/session`. Ollama base URL and any STT/TTS credentials held server-side only. Never exposed to browser.

**Topology profiles (documented, not assumed):**
1. **Local demo (default):** Browser + FastAPI + Pipecat + Ollama all on one computer. `OLLAMA_BASE_URL=http://localhost:11434`.
2. **Split local network:** Browser and backend on separate devices; Ollama on private network, not public internet.
3. **Hosted frontend/backend:** Explicitly document which inference remains local vs. what leaves the device.

**Privacy:** Microphone permission explicitly requested. No raw audio stored by default. Transcript persistence disclosed with retention controls. No logging of raw audio or sensitive transcript content.

## 6. Security, privacy, and approval model

- Secrets in server-side env vars only; `.env.example` with placeholders committed, no real secrets.
- Every seller record and tool call scoped to authenticated seller; never trust client-supplied `seller_id`.
- Seller data isolation: one seller cannot read another's transcripts, forecasts, recommendations.
- Approval required for: price changes, purchasing, budget commitments, stock updates, other consequential actions.
- Audit trail: recommendations, approvals, executions.
- No hosted LLM fallback for Ollama. If Ollama unavailable, show clear error.

## 7. Testing strategy

- **Unit tests:** KPI formulas, date/INR formatting, stock cover/reorder, forecast feature generation, recommendation prioritisation, tool validation/scoping, agent response schema, voice state machine, duplicate transcript suppression.
- **Integration tests:** API+DB, analytics+demo data, forecast+eval dataset, agent+mocked tools/Ollama, Pipecat pipeline with mocked STT/TTS/transport, recommendation approval workflow.
- **E2E tests:** Dashboard loads, text Q&A evidence-based, voice session start/speak/hear, interruption, voice failure→text fallback, recommendation approval persists.
- **Business evaluation set:** 20+ questions with required tools, expected facts, forbidden claims, expected clarifications.
- **Voice quality:** Indian English/Hinglish, SKU names/numbers, background noise, pauses, interruption, permission denied, device unplugged, network drop/reconnect, duplicate STT final events.

## 8. Risks, assumptions, open decisions

| Item | Status | Notes |
|------|--------|-------|
| Python 3.15 package compatibility | Open | Some ML/audio packages may lack 3.15 wheels. Validate at install; pin versions. |
| Pipecat version + transport API | Open | Not installed yet. Stage 08 mandates inspecting installed version before coding voice. |
| Ollama model selection | Open | Must be installed locally; model name from env var, not hardcoded. |
| STT/TTS quality for Indian English | Open | Verify faster-whisper + Piper pronunciation before finalising. |
| Database choice | Default: SQLite | PostgreSQL migration path documented for hosted deployment. |
| Agent orchestration | Default: explicit Python | LangGraph deferred unless workflow complexity justifies it. |
| Forecasting method | Default: baselines | Moving-average + seasonal-naive first; ML benchmarked later. |

## 9. Implementation sequence (stages 01–12)

Follow `docs/00_MASTER_INSTRUCTIONS.md` stage order. Stage 01 (repository audit) complete. Next: Stage 02 (product & data model).
