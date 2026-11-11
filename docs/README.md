# Virtual KAM — Stage-by-Stage AI Build Guide

This folder contains implementation briefs for an AI coding agent to build a browser-based **Virtual Key Account Manager (Virtual KAM)** for Indian marketplace sellers, from the UI through business intelligence and real-time voice.

## How to use these files

1. Put this folder in the root of your existing repository, or provide the files to your coding agent.
2. Start with `00_MASTER_INSTRUCTIONS.md`.
3. Execute the stages in numerical order. Give the agent **one stage at a time**.
4. Require it to inspect the existing repository before editing. Do not let it replace working code or invent integrations.
5. At the end of every stage, require tests, a changed-file summary, unresolved assumptions, and a clear completion report.
6. Do not proceed when a stage's acceptance criteria fail.

## Stage index

| File | Stage | Main outcome |
|---|---|---|
| `00_MASTER_INSTRUCTIONS.md` | Master brief | Product vision, global rules, architecture and delivery contract |
| `01_REPOSITORY_AUDIT.md` | Repository audit | Verified project map and implementation plan |
| `02_PRODUCT_AND_DATA_MODEL.md` | Product and data model | Seller profile, marketplace data schema, mock data and data quality |
| `03_UI_UX_FRONTEND.md` | UI/UX and frontend | Seller dashboard, KAM workspace and voice-first interface |
| `04_BACKEND_API_AND_STORAGE.md` | Backend and storage | Secure APIs, persistence, validation and service boundaries |
| `05_BUSINESS_INTELLIGENCE.md` | Business intelligence | KPI calculations, diagnosis and explainable recommendations |
| `06_FORECASTING_AND_INDIAN_SEASONALITY.md` | Forecasting | SKU demand forecasts, festival calendar and replenishment planning |
| `07_AGENT_ORCHESTRATION_AND_TOOLS.md` | KAM agent | Tool-using agent, memory, planning and approval gates |
| `08_REALTIME_VOICE_PIPECAT_OLLAMA.md` | Voice | Browser microphone → STT → local Ollama → TTS → speaker |
| `09_END_TO_END_INTEGRATION.md` | Integration | Connect UI, APIs, intelligence, agent and voice |
| `10_TESTING_AND_EVALUATION.md` | Testing | Unit, integration, voice and business-quality evaluation |
| `11_SECURITY_DEPLOYMENT_AND_PRIVACY.md` | Deployment | Secrets, local networking, deployment and operational controls |
| `12_FINAL_ACCEPTANCE_AND_HANDOFF.md` | Final review | End-to-end acceptance, demo script and technical handoff |

## Important scope note

The first release should be a **working, honest prototype**, not a pretend production system. Use mock seller data where real marketplace integrations are unavailable. Label simulated, forecasted and observed values distinctly. Do not claim a model has learned festival effects unless it has been trained and evaluated on suitable historical data.

## Suggested initial prototype defaults

These are starting recommendations, not permission to ignore the repository:

- Frontend: preserve the existing framework; if none exists, React + TypeScript + Vite.
- Backend: preserve the existing backend; otherwise FastAPI is a practical Python choice for analytics and Pipecat integration.
- LLM: Ollama with a locally installed model configured by environment variable.
- STT: local faster-whisper where hardware permits; use a replaceable provider interface.
- TTS: local Piper where a compatible voice is available; use a replaceable provider interface.
- Voice orchestration: Pipecat, with transport selected after checking the installed version and client.
- Forecasting: begin with transparent seasonal-naive / moving-average baselines; benchmark LightGBM or a time-series foundation model only when sufficient history exists.
- Storage: SQLite for a small local demo, or the repository's existing database. Keep a clean migration path to PostgreSQL.
- Agent orchestration: start with explicit Python services and typed tools. Add LangGraph only if multi-step stateful workflows justify it.

## Non-negotiable engineering principles

- Inspect before changing.
- Keep secrets on the backend.
- Business calculations must be deterministic and testable.
- The LLM must call tools for current seller facts instead of inventing numbers.
- Forecasts must show uncertainty and limitations.
- Never silently execute high-impact commercial actions.
- Voice must support visible transcripts, connection states, errors and interruption handling where the selected stack supports it.
- Verify current package APIs and versions. Never invent Pipecat imports or constructors.
