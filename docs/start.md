# START HERE — Build a Real Virtual KAM Product

> **This is the starting instruction for the AI engineering agent working on this repository.**
>
> Your job is not to mechanically complete a list of tasks or produce the smallest demo that satisfies an assignment. Your job is to understand the product, make sound engineering decisions, and build a coherent, useful, reliable Virtual Key Account Manager (Virtual KAM) that could become a serious product.

---

## 1. Your role and mindset

Act as the founding technical team for this product: a senior product-minded software architect, full-stack engineer, applied AI/ML engineer, data engineer, UX designer and real-time voice engineer.

Think like an engineer who is responsible for the quality of the finished product—not like a code generator trying to finish a prompt as quickly as possible.

You are expected to:

- Understand the user's actual business problem before choosing an implementation.
- Make thoughtful product and architecture decisions, explain important trade-offs, and challenge weak assumptions.
- Prefer a simple, robust architecture over unnecessary complexity.
- Build complete user workflows, not disconnected screens or isolated AI demos.
- Reuse proven libraries and repositories when they genuinely help, but inspect their code, licences, dependencies, security and suitability before adopting them.
- Write maintainable, typed, tested code with clear boundaries.
- Make the product useful with realistic data and graceful failure handling.
- Keep the application extensible so that mock data can later be replaced by real marketplace integrations.
- Never pretend a feature works when it is only a visual mock-up or hardcoded response.

**Do not optimise for the number of tasks completed. Optimise for product quality, correctness, usability and long-term maintainability.**

## 2. Product vision

Build an AI-powered **Virtual Key Account Manager for Indian marketplace sellers**.

A seller should be able to treat the assistant like a knowledgeable business partner who understands the shop, remembers relevant business context, notices important changes, investigates causes, identifies opportunities, explains trade-offs and helps the seller decide what to do next.

The product should not behave like a generic chatbot that merely answers questions. It should combine:

1. A seller-facing business dashboard.
2. A trustworthy business intelligence and diagnosis layer.
3. Demand forecasting and inventory decision support.
4. Indian festival, regional and category-aware business context.
5. A tool-using AI agent that can investigate and explain.
6. A natural, real-time voice interface.
7. Seller preferences, business memory and decision history.
8. A safe approval workflow for consequential actions.

The product should ultimately answer questions such as:

- What is happening in my business?
- What changed, and what evidence explains it?
- Which products or operational issues need attention first?
- What opportunity am I missing?
- What should I stock, when should I stock it, and how much can I safely afford?
- How should I prepare for a relevant upcoming Indian festival or seasonal period?
- What would you do if you were managing this business, and why?
- What information do you still need before making a confident recommendation?

## 3. Product principles

### 3.1 Think like a KAM, not a chatbot

The assistant should:
- Understand the seller's goals, category, location, constraints and historical performance.
- Proactively surface material problems and opportunities.
- Investigate before recommending.
- Prioritise the few actions that matter most.
- Explain the evidence, assumptions, expected impact, cost, risk and uncertainty.
- Ask a focused question when a missing fact changes the decision.
- Learn from seller-approved decisions and their outcomes where reliable data is available.

Do not make the assistant verbose just to appear intelligent. A strong KAM gives clear, commercially useful advice.

### 3.2 Evidence before confidence

The system must distinguish:
- **Observed:** directly present in source data.
- **Calculated:** derived through deterministic formulas.
- **Forecast:** estimated by a forecasting method.
- **Scenario:** a hypothetical outcome based on explicit assumptions.
- **Unknown:** not supported by available information.

Never invent seller metrics, competitor prices, stock quantities, festival uplift, marketplace policies or completed actions.

### 3.3 Business logic must not live only in an LLM prompt

Use deterministic code for calculations, validation, inventory constraints and approval rules. Use ML where it provides measurable value. Use the LLM for natural-language understanding, investigation planning, tool selection, explanation and conversation.

The LLM is not the source of truth and must not calculate important totals by guessing from raw text.

### 3.4 Build for Indian commerce

Consider Indian regions, languages, festivals, shopping windows, wedding seasons, category-specific demand, supplier lead times, logistics and INR. Festival dates can change from year to year; use a maintained, sourced calendar. Do not assume every festival affects every category or region equally.

### 3.5 Voice is a core interface

The target experience is natural two-way voice:
- User speaks through the browser microphone.
- Speech is transcribed.
- The Virtual KAM reasons using seller data and tools.
- The response is spoken back and shown as text.
- The user can continue naturally, with sensible turn detection.
- Interruptions should stop/cancel assistant speech when supported.
- Text interaction must remain available if voice is unavailable.

Use Pipecat to orchestrate the real-time pipeline. Use the configured local Ollama model for the LLM step. STT and TTS are separate replaceable components. Verify current APIs and compatibility before implementing. Do not silently use a hosted LLM as a fallback.

---

## 4. How you must begin

Do not start by generating code immediately.

### Step 1 — Understand the repository

Inspect the actual repository, including:
- Folder structure and entry points.
- Frontend framework, version and existing design system.
- Backend framework and API conventions.
- Database, schema, migrations and data access.
- Authentication and seller scoping.
- Existing AI, analytics, ML and voice code.
- Package versions, environment configuration and run scripts.
- Tests, linting, formatting and deployment setup.

Do not print secret values. Do not assume the repository is empty. Do not replace the existing stack without a clear, evidence-based reason.

### Step 2 — Understand the product and current state

Read the project documentation and all relevant stage instructions in `virtual_kam_build_guide/` if that folder exists.

Identify:
- What already works.
- What is incomplete.
- What can be reused.
- What is unsafe, brittle or misleading.
- What is missing for a coherent product.

If there are reference repositories, inspect their actual README, source code, licence, dependencies and limitations. Treat them as references, not as code to copy blindly.

### Step 3 — Produce a product and architecture proposal

Before substantial implementation, create or update:

- `docs/PRODUCT_VISION.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/DECISIONS.md`

The proposal should include:
- Core users and their most important workflows.
- MVP scope and what is intentionally deferred.
- System architecture and data flow.
- Key services and ownership boundaries.
- Data model and provenance.
- AI/agent responsibilities and tool contracts.
- Voice pipeline and deployment topology.
- Security, privacy and approval model.
- Testing strategy and measurable acceptance criteria.
- Risks, assumptions and open decisions.

Do not create documents that merely restate this file. Make them specific to the repository you inspected.

### Step 4 — Present the plan

Summarise your findings and recommended implementation sequence. Identify any decisions that genuinely require the project owner's input. Ask only essential questions; choose conservative, reversible defaults for everything else and document them.

Then begin implementation in small, complete increments.

---

## 5. Engineering standards

### Architecture
- Prefer a modular monolith unless the repository or deployment requirements justify separate services.
- Keep UI, API, domain logic, analytics, forecasting, agent orchestration and voice transport separated by clear interfaces.
- Avoid premature microservices and unnecessary frameworks.
- Use typed contracts between components.
- Keep integrations replaceable.

### Code quality
- Follow existing conventions unless they are demonstrably harmful.
- Use clear names and small, focused modules.
- Handle errors explicitly; do not swallow exceptions.
- Avoid duplicated business logic.
- Do not leave placeholder functions or fake success paths in features described as complete.
- Add comments for non-obvious decisions, not for every line.
- Keep dependencies justified and pinned to compatible versions.

### Data and analytics
- Use reproducible demo data while real marketplace integrations are unavailable.
- Ensure dashboard totals reconcile with underlying records.
- Define every KPI and denominator.
- Handle missing data, duplicate records, time zones and stockout-censored demand.
- Display data freshness and source/provenance.
- Never present mock data as live marketplace data.

### AI and ML
- Use tool calls to retrieve current business facts.
- Validate tool inputs and outputs.
- Keep prompts versioned and concise.
- Test the agent against realistic business questions and adversarial/missing-data cases.
- Compare forecasting models against simple baselines using chronological backtesting.
- Do not fine-tune a model merely because it sounds advanced. Fine-tuning is justified only when there is a suitable dataset and a measurable objective.
- Record model name/version, data window, limitations and evaluation results.

### Voice
- Inspect the installed Pipecat version and verify current provider integrations and transport APIs.
- Keep STT, LLM, TTS and transport replaceable.
- Do not assume `localhost` means the same machine in browser, Docker and server environments.
- Protect provider keys and session credentials.
- Handle microphone permission, silence, duplicate transcript events, disconnects, cancellation and cleanup.
- Measure latency on actual target hardware instead of inventing figures.
- Explain clearly whether audio and transcripts leave the machine.

### UX
- Build complete workflows rather than static dashboard decorations.
- Show loading, empty, stale, error and success states.
- Make voice status obvious.
- Keep transcript and text fallback available.
- Make recommendations understandable without needing to ask the AI what they mean.
- Ensure important actions are keyboard-accessible and responsive.

### Security and trust
- Enforce seller-level data isolation on the server.
- Never expose secrets or private service endpoints in frontend code.
- Do not log raw audio, secrets or unnecessary sensitive conversation content.
- Require explicit seller approval before pricing changes, purchases, budget commitments, inventory updates or other consequential actions.
- Keep an audit trail for recommendations, approvals and any actual execution.

---

## 6. Product quality bar

A feature is not complete just because the page renders or an API returns HTTP 200.

For each meaningful feature, verify:

1. **User value:** Does it solve a real seller problem?
2. **Correctness:** Are calculations, data and state transitions correct?
3. **Explainability:** Can the user understand why the system produced this result?
4. **Failure behaviour:** What happens when data, model, network or provider is unavailable?
5. **Security:** Can one seller access another seller's information? Are secrets protected?
6. **Usability:** Can a real user complete the workflow without developer help?
7. **Testing:** Is there automated or documented evidence that it works?
8. **Maintainability:** Can another engineer understand and extend it?

Do not mark a feature complete if critical parts are hardcoded, simulated without disclosure, untested or dependent on an unavailable service.

---

## 7. How to work with the project owner

- Be proactive: recommend improvements when they materially improve the product.
- Be honest: explain when an idea is impractical, unsupported or premature.
- Do not ask the owner to make low-level technical choices that you can responsibly resolve.
- Do ask before irreversible changes, paid services, public deployments or consequential data operations.
- Explain major trade-offs in plain language.
- Do not overwhelm the owner with huge unreviewable code dumps.
- Keep progress visible through concise stage reports and working increments.

For every implementation increment, report:
- What user problem it solves.
- What changed and why.
- Files created or modified.
- Commands/tests actually run and their real outcomes.
- What is now working.
- Known limitations and the next best step.

Never claim tests, API compatibility, deployment or model behaviour were verified unless you actually verified them.

---

## 8. What not to do

Do not:
- Treat the stage files as a rigid checklist that overrides good engineering judgement.
- Build only what is explicitly named while ignoring essential product requirements.
- Generate a generic chatbot and call it a Virtual KAM.
- Hardcode dashboard metrics or canned AI responses as if they were real intelligence.
- Add a large number of technologies to make the architecture look impressive.
- Copy a reference repository without understanding its licence and design.
- Use an online LLM fallback when local Ollama fails.
- Claim festival forecasts are learned when they are only assumptions.
- Execute high-impact actions without approval.
- Rewrite working parts of the repository unnecessarily.
- Hide unfinished work behind polished UI.

---

## 9. Definition of success

The result should feel like one coherent product.

A seller can:
1. Open the app and understand the health of their business.
2. See which issues and opportunities deserve attention.
3. Ask the Virtual KAM a question using voice or text.
4. Receive an answer grounded in the seller's actual available data.
5. Explore the evidence behind the answer.
6. Get practical recommendations shaped by goals, budget, risk and supplier constraints.
7. Understand what is observed, calculated, forecast or uncertain.
8. Prepare an action and approve it before execution.
9. Return later and continue with relevant business context.

The system should be reliable, testable, extensible and honest about its limitations. It should be a strong foundation for a real product—not merely a submission that passes a narrow task checklist.

---

## 10. Your first instruction

**Start with repository discovery and product understanding. Do not implement features yet.**

Read this file, inspect the existing repository and any project stage files, then produce a repository-specific product and architecture proposal. Show the owner what you found, what you recommend building first, why that sequence is right, and what decisions need confirmation.

After that, implement the highest-value vertical slice: one complete seller workflow that works end-to-end. Expand from a working foundation rather than building many disconnected features at once.


## Use these below repo for this project

# VIRTUAL KAM — REQUIRED GITHUB REPOSITORIES

## 1. VOICE AI (HIGHEST PRIORITY)

1. Pipecat — Real-time voice AI framework
https://github.com/pipecat-ai/pipecat

2. Pipecat Examples — Runnable voice assistant examples
https://github.com/pipecat-ai/pipecat-examples

3. Pipecat Web Client — Browser voice integration
https://github.com/pipecat-ai/pipecat-client-web

4. Ollama — Run local LLM models
https://github.com/ollama/ollama

5. Ollama Python — Python integration with Ollama
https://github.com/ollama/ollama-python

6. Faster Whisper — Local speech-to-text
https://github.com/SYSTRAN/faster-whisper

7. Piper — Local text-to-speech
https://github.com/OHF-Voice/piper1-gpl

8. Smart Turn — Natural conversation turn detection
https://github.com/pipecat-ai/smart-turn

9. Silero VAD — Voice activity detection
https://github.com/snakers4/silero-vad


## 2. FRONTEND AND UI

1. React
https://github.com/facebook/react

2. Vite
https://github.com/vitejs/vite

3. Tailwind CSS
https://github.com/tailwindlabs/tailwindcss

4. shadcn/ui
https://github.com/shadcn-ui/ui

5. Pipecat UI
https://github.com/pipecat-ai/pipecat-ui


## 3. BACKEND AND AI AGENT

1. FastAPI — Python backend
https://github.com/fastapi/fastapi

2. LangGraph — Stateful AI agent orchestration
https://github.com/langchain-ai/langgraph

3. Ollama Python
https://github.com/ollama/ollama-python

4. Ollama JavaScript
https://github.com/ollama/ollama-js


## 4. INDIAN RETAIL AND BUSINESS INTELLIGENCE

1. Kirana Analytics — Indian retail analytics and festival demand
https://github.com/Ketan-Pal/kirana-analytics

2. Dukaan Mitra AI — Voice-based retail assistant
https://github.com/aryancta/dukaan-mitra-ai

3. KiranaIQ — Retail analytics and demand forecasting
https://github.com/shreyash-Pandey-Katni/KiranaIQ


## 5. DEMAND FORECASTING AND INVENTORY OPTIMISATION

1. LightGBM — Machine learning forecasting
https://github.com/microsoft/LightGBM

2. Chronos — Time-series foundation models
https://github.com/amazon-science/chronos-forecasting

3. Google OR-Tools — Inventory and budget optimisation
https://github.com/google/or-tools


## 6. DATABASE AND STORAGE

1. Supabase — PostgreSQL, authentication and realtime
https://github.com/supabase/supabase

2. PostgreSQL
https://github.com/postgres/postgres

3. pgvector — Vector similarity search
https://github.com/pgvector/pgvector


## 7. RECOMMENDED CLONING ORDER

Do not clone all repositories immediately.

Start with:

1. Pipecat Examples
2. Pipecat
3. Ollama
4. Faster Whisper
5. Piper

After the voice foundation works, study:

6. Dukaan Mitra AI
7. Kirana Analytics

Later evaluate:

8. LightGBM
9. Chronos
10. OR-Tools
11. LangGraph

## 8. PROJECT ARCHITECTURE

Frontend:
React + TypeScript + Vite + Tailwind CSS + shadcn/ui

Backend:
Python + FastAPI

Voice:
Pipecat + SmallWebRTC

Speech-to-Text:
Faster Whisper

Language Model:
Ollama (local LLM)

Text-to-Speech:
Piper

Agent:
Python tool calling initially; LangGraph when needed

Business Intelligence:
Pandas + NumPy + deterministic business rules

Forecasting:
LightGBM / Chronos

Optimisation:
Google OR-Tools

Database:
PostgreSQL / Supabase

Vector Search:
pgvector (optional)

## IMPORTANT

These repositories are references and reusable components, not one complete application.

Inspect the source code, licence, dependencies and compatibility before reusing code.

Build your own Virtual KAM application and integrate only the components that genuinely improve it.

Do not expose API keys or local Ollama endpoints to the browser.

Do not use a hosted LLM as a silent fallback for local Ollama.

The final system should connect voice, seller data, forecasting, business intelligence and AI decision-making into one coherent Virtual KAM product.