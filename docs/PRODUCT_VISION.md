# Product Vision — Virtual KAM

**Repository:** `virtual-kam` (repository root)  
**Product:** AI-powered Virtual Key Account Manager for Indian marketplace sellers  
**Status:** Proposal (pre-implementation)

## 1. Core users and most important workflows

### Primary user: Indian marketplace seller
- Runs a shop on an Indian e-commerce marketplace (mock/Snapdeal-like; no live integration assumed).
- May not be technical; needs clear, actionable advice in INR with Indian date/festival context.
- Has limited time; wants to know what needs attention *today*, not a wall of metrics.

### Most important workflows (MVP)

| Workflow | User goal | Outcome |
|----------|-----------|---------|
| Dashboard review | "What is happening in my business?" | See KPIs (revenue, orders, units, ASP, cancellation, return, stockout), period-over-period change, and "what needs attention today." |
| Voice/text investigation | "Why are my sales down this month?" | Ask in natural language; get an evidence-based answer citing metrics, periods, and affected SKUs. |
| Replenishment planning | "What should I restock before Diwali?" | Get a forecast-informed replenishment plan with lead time, stock, incoming stock, budget, and assumptions. |
| Recommendation approval | "Prepare this action for me." | Review a draft recommendation (evidence, impact range, cost, risk, confidence) and approve/reject. |
| Settings | "My budget, margin floor, risk tolerance." | Configure business constraints that shape every recommendation. |

## 2. MVP scope and what is intentionally deferred

### In scope (MVP)
- Seller profile, product/SKU catalogue, daily performance, inventory snapshots, calendar events (mock, deterministic).
- Deterministic KPI calculations (revenue, orders, units, ASP, cancellation, return, conversion, stock cover, reorder quantity).
- Rule-based diagnosis engine (revenue down → order volume, stockouts, cancellations).
- Prioritised, seller-aware recommendations with approval workflow.
- Text chat with the Virtual KAM agent (typed tools, evidence-based answers).
- Real-time voice (Pipecat + Ollama + faster-whisper + Piper) with transcript, text fallback, and state machine.
- Seller settings influencing recommendations (budget, risk tolerance, margin floor, stock cover days, lead time, storage).
- Audit trail of recommendations and approvals.

### Intentionally deferred (post-MVP)
- Live marketplace API integration (Snapdeal or other). Mock data only; clearly labelled.
- LangGraph agent orchestration (start with explicit Python tool orchestration; add LangGraph only if workflow complexity justifies it).
- LightGBM / Chronos forecasting (start with moving-average + seasonal-naive baselines; benchmark ML models only after sufficient history and baseline evaluation).
- pgvector / vector search (not needed for MVP).
- Raw audio storage (not stored by default).
- Multi-seller concurrency at scale (single-user SQLite prototype; PostgreSQL migration path documented).

## 3. Product principles (from start.md)

- **KAM, not chatbot:** Investigate before recommending; prioritise few actions that matter; explain evidence, assumptions, impact, cost, risk, uncertainty; ask one focused question when a fact is missing.
- **Evidence before confidence:** Distinguish observed / calculated / forecast / scenario / unknown. Never invent metrics, competitor prices, dates, stock, or completed actions.
- **Business logic in code, not only prompts:** Deterministic KPIs, validation, inventory constraints, approval rules in code. LLM for understanding, planning, tool selection, explanation, conversation.
- **Indian commerce:** INR, Indian regions, festivals (sourced calendar with provenance), wedding season, category-specific demand, supplier lead times.
- **Voice is core:** Natural two-way voice; browser mic → STT → agent → TTS → speaker; text fallback always available; interruptions where supported.
- **Safety:** No high-impact action without explicit seller approval. Secrets on server only. No hosted LLM fallback for Ollama.

## 4. What success looks like (MVP)

A seller can open the app, view dashboard KPIs, ask by voice or text why sales changed, receive an evidence-based answer grounded in their actual (mock) data, see a replenishment recommendation with uncertainty and budget, approve it, and return later with context preserved. The system remains usable if voice is unavailable (text fallback).
