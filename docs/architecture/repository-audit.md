# Repository Audit — Virtual KAM

**Stage:** 01 — Repository Audit and Technical Plan  
**Status:** Verified facts + recommendations  
**Date:** 2026-11-10

---

## 1. Verified repository structure

| Path | Type | Notes |
|------|------|-------|
| `main.py` | File | 20 bytes, contains only `print('hello world')` |
| `docs/` | Directory | 13 stage briefs (00–12) plus README.md |
| `docs/README.md` | File | Stage-by-stage build guide |

**Confirmed absent:** No `requirements.txt`, `pyproject.toml`, `package.json`, `setup.py`, `Pipfile`, `poetry.lock`, `.env`, `.env.example`, `docker-compose.yml`, `Dockerfile`, test directories, source directories, frontend code, backend code, database files, migrations, or voice/AI code.

**Git:** Not a git repository (`git status` → fatal: not a git repository).

---

## 2. Verified runtime environment

| Item | Value | Verified via |
|------|-------|--------------|
| Python | 3.15.0 (tags/v3.15.0, Oct 9 2026, MSC v.1951 64 bit AMD64) | `python --version` |
| Python executable | `C:\Program Files\Python315\python.exe` | `sys.executable` |
| pip | 26.2.1 | `pip --version` |
| Installed packages | `pip` only (no other packages) | `pip list` |
| OS | Windows (win32), PowerShell | Shell execution |

**No virtual environment is active.** No Python packages beyond pip are installed.

---

## 3. Current architecture and request/data flow

There is no application architecture yet. `main.py` is a placeholder that prints `hello world` and does not serve HTTP, connect to a database, or handle audio.

**Request/data flow:** None exists.

---

## 4. Dependency/version summary

Only the Python standard library and `pip` are available. None of the following are installed:
- Web framework (FastAPI, Flask, Django, etc.)
- Frontend framework (React, Vite, etc.)
- Database/ORM (SQLAlchemy, SQLite driver beyond stdlib, etc.)
- Pipecat
- faster-whisper
- Piper TTS
- Ollama client
- LangGraph
- Testing frameworks (pytest, etc.)

---

## 5. Existing reusable components

**None.** No UI components, API routes, database models, voice code, or AI integrations exist in the repository.

---

## 6. Missing capabilities for Virtual KAM

Every capability listed in the product docs is missing:

| Capability area | Missing |
|-----------------|---------|
| Frontend (React/Vite/TypeScript) | Not present |
| Backend API framework | Not present |
| Database / ORM / migrations | Not present |
| Authentication / authorisation | Not present |
| Typed API schemas | Not present |
| KPI calculation service | Not present |
| Diagnosis engine | Not present |
| Recommendation service | Not present |
| Forecasting service | Not present |
| Festival calendar data | Not present |
| KAM agent + tool orchestration | Not present |
| Pipecat voice service | Not present |
| STT (faster-whisper) | Not installed |
| TTS (Piper) | Not installed |
| Ollama integration | Not installed |
| Audio transport (WebRTC/WebSocket) | Not present |
| Voice state machine (client) | Not present |
| Test suite (unit/integration/E2E) | Not present |
| Linting / type-checking config | Not present |
| Environment config (`.env.example`) | Not present |
| Deployment files (Docker, docker-compose) | Not present |

---

## 7. Risks and compatibility issues

| Risk | Description | Mitigation |
|------|-------------|------------|
| Greenfield build | Everything must be built from scratch; no existing stack to preserve | Follow docs 02–12 in order; choose conservative defaults |
| Python 3.15 | Very new; some ML/audio packages may lack wheels for 3.15 | Validate package compatibility at install time; pin versions |
| No package manager config | No `requirements.txt` or `pyproject.toml` exists | Create one as part of Stage 02–04 |
| Pipecat version unknown | Not installed; must verify before coding voice stage | Stage 08 mandates inspecting installed Pipecat version before coding |
| Ollama not installed | Local LLM dependency must be installed separately | Document Ollama install + model download in Stage 08 |
| Windows-only verification so far | Environment checked on Windows; cross-platform not tested | Document Windows as primary dev platform; note where paths differ |

---

## 8. Proposed architecture (extends the current project)

Since the repository is empty, the proposed architecture is a **new modular monolith** hosted in one Python application (FastAPI), with a separate TypeScript/Vite frontend. This matches the docs' guidance: "A modular monolith is acceptable for the prototype" and "Do not create microservices without a concrete deployment or scaling reason."

### Component map

```
Browser (Vite + TypeScript + React)
  │ HTTPS/WebSocket/WebRTC
  ▼
Backend (FastAPI, Python 3.15)
  ├── Seller & catalogue API          (/api/seller, /api/products)
  ├── Analytics/KPI service           (/api/dashboard, /api/analytics)
  ├── Forecasting service             (/api/forecasts)
  ├── Recommendation service          (/api/recommendations)
  ├── KAM agent service               (/api/assistant/chat)
  └── Voice session service           (/api/voice/session) → Pipecat
  │
  ├── SQLite (local demo) / PostgreSQL (hosted)
  └── Ollama (http://localhost:11434) — local LLM only
        ├── STT: faster-whisper (local)
        └── TTS: Piper (local)
```

### Service boundaries (per docs 04)

1. Seller and catalogue service
2. Analytics/KPI service
3. Forecasting service
4. Recommendation/decision service
5. KAM agent service
6. Voice session service (Pipecat)
7. Persistence and audit service

All seven initially live in one FastAPI application (modular monolith), with clear internal module separation.

### Storage decision

- **SQLite** for the single-user local prototype (per docs 04: acceptable for local prototype)
- Migration path to **PostgreSQL** documented for hosted/concurrent deployment
- Schema/migrations kept explicit and repeatable

### Voice transport decision (to be verified in Stage 08)

Per docs 08, the transport must be chosen after inspecting the installed Pipecat version. Since Pipecat is not installed yet, this remains an open decision. Recommended starting point: a Pipecat-supported WebRTC transport if compatible; WebSocket only if genuinely appropriate for streaming/interruption. Do not assume `localhost` equivalence across browser, container, and backend.

### Session scoping without exposing secrets

The frontend obtains a scoped session token from the backend (`POST /api/voice/session`). The backend holds the Ollama base URL and any STT/TTS credentials server-side. The browser never receives Ollama URLs, provider keys, or internal service URLs.

### Expected topology (documented, not assumed)

**Local demo (default):** Browser + FastAPI backend + Pipecat + Ollama all on one computer. `OLLAMA_BASE_URL=http://localhost:11434` resolves correctly because all services are on the same host.

**Split local network:** Browser and backend on separate devices; Ollama reachable only on private network; backend configures Ollama address via env var, never exposed to browser.

**Do not** assume Docker `localhost` refers to the host; if containerised, use host networking or the correct container reachable address.

---

## 9. Ordered implementation plan

Follow the 12 stages in numerical order as defined in `docs/README.md` and `docs/00_MASTER_INSTRUCTIONS.md`.

| Stage | File | Main outcome | Exact files likely to change/create |
|-------|------|--------------|-------------------------------------|
| 01 | `01_REPOSITORY_AUDIT.md` | Verified project map + plan | `docs/architecture/repository-audit.md` (this file) |
| 02 | `02_PRODUCT_AND_DATA_MODEL.md` | Data model + mock data | `backend/app/models/`, `backend/app/db/`, `backend/app/data/` |
| 03 | `03_UI_UX_FRONTEND.md` | Dashboard + KAM workspace | `frontend/src/` (React + Vite + TypeScript) |
| 04 | `04_BACKEND_API_AND_STORAGE.md` | Secure APIs + persistence | `backend/app/api/`, `backend/app/services/`, migrations |
| 05 | `05_BUSINESS_INTELLIGENCE.md` | KPIs, diagnosis, recommendations | `backend/app/bi/`, `backend/app/diagnosis/` |
| 06 | `06_FORECASTING_AND_INDIAN_SEASONALITY.md` | Forecasts + festival calendar | `backend/app/forecasting/`, `backend/app/calendar/` |
| 07 | `07_AGENT_ORCHESTRATION_AND_TOOLS.md` | KAM agent + tools | `backend/app/agent/`, `backend/app/tools/` |
| 08 | `08_REALTIME_VOICE_PIPECAT_OLLAMA.md` | Pipecat voice pipeline | `backend/app/voice/`, `frontend/src/voice/` |
| 09 | `09_END_TO_END_INTEGRATION.md` | Connect all services | Integration wiring across backend + frontend |
| 10 | `10_TESTING_AND_EVALUATION.md` | Tests + eval set | `tests/`, `backend/tests/`, `frontend/tests/` |
| 11 | `11_SECURITY_DEPLOYMENT_AND_PRIVACY.md` | Security + deployment | `.env.example`, deployment docs, health checks |
| 12 | `12_FINAL_ACCEPTANCE_AND_HANDOFF.md` | Handoff report | `docs/FINAL_HANDOFF.md` |

**First action (per master instructions):** Execute Stage 01 only. This audit is complete; do not begin Stage 02 until Stage 01 acceptance criteria are confirmed.

---

## 10. Stage 01 acceptance criteria check

| Criterion | Status |
|-----------|--------|
| Existing stack and versions verified from repository files or runtime commands | ✅ Python 3.15.0, pip 26.2.1, no other packages |
| No application code modified during audit unless necessary and documented | ✅ No code modified |
| Existing audio/AI code is identified | ✅ None exists (confirmed absent) |
| Proposed architecture compatible with actual repository | ✅ Modular monolith proposed for empty repo |
| `docs/architecture/repository-audit.md` exists and distinguishes verified facts from recommendations | ✅ This document |
| Next stage can begin without guessing the project's structure | ✅ Structure fully documented |

Stage 01 is complete. The repository is a blank slate with only `main.py` and the 13 docs. Stage 02 (Product and Data Model) can begin next.
