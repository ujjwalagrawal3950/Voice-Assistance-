# Virtual KAM — AI Voice & Business Partner

Local-first AI Key Account Manager (KAM) for marketplace sellers featuring two-way voice conversation (Edge Neural Indian-English TTS with offline Piper fallback, faster-whisper streaming captions, persistent cross-page VoiceProvider), root-cause revenue decomposition, stockout impact quantification, what-if planning, proactive alerts, seller decision profiles, recommendation outcome tracking, and ChatGPT-style previous chats.

## Running Locally

Use `start-all.bat` or start the three services:
1. **Backend API (`:8000`)**: `.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --port 8000`
2. **Voice Service (`:8765`)**: `.venv-voice\Scripts\python.exe voice-service\main.py`
3. **Frontend (`:5173`)**: `npm --prefix frontend run dev`

## Previous Chats Title Rule

Session titles are generated deterministically **once** on session creation (`POST /sessions`) from the user's first message via `make_title(first_user_message)` in `backend/app/api/sessions.py` (never using an LLM, and never regenerated on later messages):

1. Strip leading whitespace and common greeting prefixes (`hi`, `hello`, `hey`, `namaste`).
2. Take the first clause/sentence before `.`, `!`, `?`, or newline.
3. Truncate cleanly to 50 characters; fall back to `"New chat"` if empty.

Examples:
- `"My sales have dropped this month. Can you help?"` -> `"My sales have dropped this month"`
- `"hey, why are my cancellations rising?"` -> `"why are my cancellations rising"`
- `"hi"` -> `"New chat"`

