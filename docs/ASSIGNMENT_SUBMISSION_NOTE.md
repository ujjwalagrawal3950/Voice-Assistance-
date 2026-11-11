# Virtual KAM — Mini AI Voice Key Account Manager (Snapdeal Seller Assistant)

## 1. Overview & Business Scenario
Virtual KAM is a browser-based, two-way AI voice assistant built for Snapdeal marketplace sellers. When a seller opens a call and asks *"My sales have dropped significantly this month. I don't understand why. Can you help me?"*, the assistant greets the seller, inspects deterministic seller KPIs, diagnoses root causes across **inventory, cancellations, pricing, and visibility**, asks focused follow-up questions, recommends 2–3 prioritized practical actions, and summarizes the call with next steps.

---

## 2. Models & Voice Stack (100% Local-First + Browser Fallback)

| Component | Technology | Role |
|---|---|---|
| **LLM (Reasoning & Dialogue)** | **Ollama (`llama3.1:8b`)** | Natural two-way dialogue, follow-up questioning, action prioritization, and call summary generation — strictly grounded in tool outputs |
| **Speech-to-Text (STT)** | **faster-whisper (`base`)** + **Web Speech API preview** | Local CPU transcription of browser WebM/Opus microphone audio via PyAV (`16 kHz` mono) with real-time live captions in chat |
| **Text-to-Speech (TTS)** | **Piper (`en_US-lessac-medium`)** + **Web Speech Synthesis fallback** | Fast local WAV speech synthesis streamed back over WebSocket to the browser speaker |
| **Audio Transport & Turn-Taking** | **WebSockets + Client RMS VAD** | Adaptive ambient-noise threshold + `1.2s` silence auto-end-of-turn + manual **Send voice** and **Interrupt** (barge-in) controls |
| **Backend & Database** | **FastAPI (Python 3.15) + SQLite** | Deterministic KPI calculations (`kpi.py`), typed agent tools (`tools.py`), approval-gated recommendations (`/api/recommendations`) |
| **Frontend** | **React 19 + TypeScript + Vite + Tailwind CSS v4** | Live voice/text workspace, Seller Overview KPI dashboard, Product/SKU table, Recommendations approval queue, and Seller Settings |

---

## 3. End-to-End Workflow
1. **Greeting:** Clicking **Start Voice** connects to `ws://localhost:8765` (with automatic browser Web Speech API fallback if `voice-service` is offline), and immediately greets the seller aloud.
2. **Real-Time Listening & Live Captions:** As the seller speaks, live words appear continuously in a user bubble inside the chat thread (`SpeechRecognition` preview when available + `faster-whisper` `audio_partial` snapshots).
3. **Deterministic Investigation (Zero Hallucinated Metrics):** On turn completion, `voice-service` transcribes the full utterance via `faster-whisper` and calls `POST /api/assistant/chat` (`channel="voice"`). The backend executes deterministic Python KPI tools against SQLite before invoking `llama3.1:8b`.
4. **Data Diagnosis & Assumptions (Sample Seller Data Reconciliation):**
   - **Sales:** ₹2,00,000 → ₹1,35,000 (**-32.5%**) | **Orders:** 400 → 270 (**-32.5%**)
   - **Average Selling Price:** **₹500 → ₹500** (unchanged — rules out pricing erosion)
   - **Out-of-stock SKUs:** **5 → 18** (+13 fast-moving SKUs stocked out)
   - **Cancellation Rate:** **8% → 14.1%** (+6.1pp) | **Catalog Views:** **-29.5%** (due to out-of-stock listing suppression)
   - *Explicit Assumptions:* Higher cancellations are assumed to stem primarily from oversold stockouts or dispatch delays rather than buyer COD refusals; replenishment recommendations assume 3–5 day supplier lead times within the seller's ₹40,000 budget and ≥25% margin target.
5. **Action & Call Wrap-Up:** The KAM asks diagnostic follow-up questions, proposes 2–3 prioritized actions (restock top stockout SKUs, enforce stock buffers/24h dispatch SLA, boost visibility on active ₹500 SKUs), and generates a concise spoken & written summary when **Summarize** is clicked or requested. High-impact actions are queued in **Recommendations** for explicit **Approve / Reject** action by the seller.

