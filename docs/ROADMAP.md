# Roadmap — Virtual KAM

**Repository:** `virtual-kam` (repository root)  
**Status:** Proposal  
**Method:** 12 stages in order (per `docs/00_MASTER_INSTRUCTIONS.md`), each with acceptance criteria. Implement one complete vertical slice end-to-end before expanding.

## Stage-by-stage plan

| Stage | Focus | Primary deliverables | Depends on |
|-------|-------|---------------------|------------|
| 01 | Repository audit | `docs/architecture/repository-audit.md` (complete) | — |
| 02 | Product & data model | SQLAlchemy models, migrations, deterministic mock data, API schemas | 01 |
| 03 | UI/UX frontend | React + Vite + Tailwind + shadcn/ui: dashboard, KAM workspace, SKU view, recommendations, settings | 02 (API contracts) |
| 04 | Backend API & storage | FastAPI routes, seller scoping, validation, SQLite persistence | 02 |
| 05 | Business intelligence | Deterministic KPIs, diagnosis engine, structured recommendations | 02, 04 |
| 06 | Forecasting & Indian seasonality | Baseline forecast, festival calendar, replenishment calculation | 02, 04 |
| 07 | Agent orchestration & tools | Typed tools, KAM agent, memory, approval gates | 02, 04, 05 |
| 08 | Real-time voice (Pipecat + Ollama) | Voice pipeline, STT/TTS/transport, client state machine | 04, 07 |
| 09 | End-to-end integration | Connect frontend, backend, BI, forecasting, agent, voice | 03–08 |
| 10 | Testing & evaluation | Unit/integration/E2E tests, business eval set, voice quality tests | 02–09 |
| 11 | Security, deployment & privacy | `.env.example`, health checks, deployment profiles, startup validation | 01–10 |
| 12 | Final acceptance & handoff | `docs/FINAL_HANDOFF.md`, demo script, test results, known limitations | 01–11 |

## Highest-value first vertical slice

Per `docs/start.md` Step 10: implement one complete seller workflow end-to-end before building disconnected features.

**Slice: "Why are my sales down?" → evidence → recommendation → approval**

1. Backend: seller profile + dashboard KPIs + mock data (revenue decline scenario).
2. Frontend: dashboard rendering KPIs from backend.
3. Agent: text chat answering "why are sales down" using dashboard/SKU/inventory tools.
4. Frontend: text chat UI with transcript and evidence display.
5. Approval: create recommendation → seller approves/rejects → persists.

This slice exercises: data model, API, deterministic KPIs, diagnosis, agent tools, text chat, UI, and approval workflow — the core product loop. Voice (Stage 08) and forecasting (Stage 06) build on top.

## Acceptance gate before proceeding to next stage

Each stage must:
- Pass its acceptance criteria (per stage doc).
- Run tests, lint, type checks.
- Report exact commands and actual outcomes.
- List created/modified files.
- List known limitations and next-stage dependencies.
- Confirm each acceptance criterion explicitly.

Do not proceed when a stage's acceptance criteria fail.
