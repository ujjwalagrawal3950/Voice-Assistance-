# Decisions — Virtual KAM

**Repository:** `virtual-kam` (repository root)  
**Status:** Proposal  
**Convention:** Decisions are logged here with reason, alternatives considered, and status (proposed / accepted / deferred / rejected). Conservative, reversible defaults are chosen where the owner has not expressed a preference.

## D-001: Backend framework — FastAPI (accepted)
- **Reason:** Python, async-friendly, automatic OpenAPI/docs, strong typing with Pydantic, well-suited to analytics + Pipecat integration. Matches docs 04 suggested stack and start.md recommendation.
- **Alternatives considered:** Flask, Django. Rejected: Flask lacks built-in validation/OpenAPI; Django is heavier than needed for a modular monolith prototype.
- **Status:** Accepted

## D-002: Frontend framework — React + TypeScript + Vite + Tailwind CSS + shadcn/ui (accepted)
- **Reason:** Matches start.md recommended stack, strong ecosystem, component library for B2B analytics UI, TypeScript for typed contracts with backend.
- **Alternatives considered:** None strongly; preserve existing framework if present (none exists).
- **Status:** Accepted

## D-003: Database — SQLite for local demo, PostgreSQL migration path documented (accepted)
- **Reason:** docs 04 permits SQLite for single-user local prototype; zero-config startup; clear migration path to PostgreSQL for concurrent/hosted.
- **Alternatives considered:** PostgreSQL from day one. Rejected: adds operational complexity unnecessary for MVP.
- **Status:** Accepted

## D-004: ORM — SQLAlchemy (accepted)
- **Reason:** Mature Python ORM, supports SQLite and PostgreSQL, explicit migrations via Alembic, matches "schema/migrations explicit" requirement.
- **Alternatives considered:** SQLModel (FastAPI-native). Rejected: SQLAlchemy + Alembic is more explicit for migrations; acceptable either way.
- **Status:** Accepted

## D-005: Authentication — seller-scoped session, no third-party auth for MVP (accepted)
- **Reason:** docs 11 says "use existing authentication if present" — none exists. Single-user prototype; seller identity from secure session cookie/header. No Clerk/Auth0 unless owner requests.
- **Alternatives considered:** Clerk, Supabase Auth. Rejected: adds external dependency and complexity not needed for MVP.
- **Status:** Accepted (owner may request real auth later)

## D-006: LLM — Ollama (local only), no hosted fallback (accepted)
- **Reason:** docs 08 mandates Ollama only; no OpenAI fallback; local privacy; matches "no hosted LLM" principle.
- **Alternatives considered:** OpenAI API. Rejected: violates core product principle and privacy requirements.
- **Status:** Accepted

## D-007: STT — faster-whisper (local) (accepted, default)
- **Reason:** docs 08 recommended default; local audio; replaceable interface.
- **Open:** Model size and hardware compatibility to be verified (Python 3.15 wheel availability).
- **Status:** Accepted (default; verify in Stage 08)

## D-008: TTS — Piper (local) (accepted, default)
- **Reason:** docs 08 recommended default; local audio; replaceable interface.
- **Open:** Voice model path and Indian English/Hinglish pronunciation to be verified.
- **Status:** Accepted (default; verify in Stage 08)

## D-009: Voice orchestration — Pipecat (accepted)
- **Reason:** docs 08 mandates Pipecat; real-time pipeline orchestration; replaceable transport.
- **Open:** Transport (WebRTC vs WebSocket) to be verified against installed Pipecat version.
- **Status:** Accepted

## D-010: Voice transport — TBD (open)
- **Reason:** Must inspect installed Pipecat version before choosing. Preferred: Pipecat-supported WebRTC transport. WebSocket only if genuinely appropriate.
- **Status:** Open — decide in Stage 08

## D-011: Agent orchestration — explicit Python tool orchestration for MVP; LangGraph deferred (accepted)
- **Reason:** docs 07 says start with explicit orchestration; add LangGraph only if workflow needs persistent state, branching, retries, or human-approval checkpoints.
- **Status:** Accepted

## D-012: Forecasting — moving-average + seasonal-naive baselines first; ML benchmarked later (accepted)
- **Reason:** docs 06 says start with transparent baseline; benchmark LightGBM/Chronos only when sufficient history exists and baseline is evaluated.
- **Status:** Accepted

## D-013: Currency — integer paise, displayed as INR (accepted)
- **Reason:** docs 02 data quality requirement; avoids floating-point errors.
- **Status:** Accepted

## D-014: Mock data only; no Snapdeal or live marketplace integration (accepted)
- **Reason:** docs 00 and 02: no Snapdeal API access assumed; deterministic reproducible mock data; clearly labelled as mock/observed/derived.
- **Status:** Accepted

## D-015: Provenance labelling — observed / calculated / estimated / forecast / simulated (accepted)
- **Reason:** docs 00 global rule and docs 02 evidence principles.
- **Status:** Accepted

## D-016: Approval required for consequential actions (accepted)
- **Reason:** docs 00, 07, 11: price changes, purchasing, budget commitments, stock updates need explicit seller approval.
- **Status:** Accepted

## Open decisions requiring owner input

| Decision | Why it needs input | Options |
|----------|-------------------|---------|
| Real marketplace integration (Snapdeal/other) | Requires API access, credentials, terms of service | Defer to post-MVP; or owner can provide sandbox access |
| Third-party authentication (Clerk/Auth0) | Owner may want real user accounts vs. single-user demo | Add now or defer |
| Deployment target (local only vs. hosted) | Affects database choice, networking, security setup | Local demo MVP; hosted profile documented |
