"""Virtual KAM Voice Service — Local STT (faster-whisper) → KAM Agent (Ollama) → TTS (Piper).

Runs on Python 3.13 (.venv-voice) and exposes a bidirectional WebSocket server
on port 8765 for real-time browser voice conversations.

Flow:
  Browser Mic (WebM/Opus or WAV)
    → WebSocket partial snapshots ({"type": "audio_partial", "data": "<b64>"}) → {"type": "partial_transcript"}
    → WebSocket binary chunks + {"type": "audio_end"}
    → PyAV decode & resample (16 kHz mono float32)
    → faster-whisper local STT
    → Backend POST /api/assistant/chat (channel="voice", Ollama + deterministic tools)
    → Piper local TTS (WAV)
    → WebSocket JSON transcript/response + binary WAV audio → Browser Speaker
"""

import os

# Prevent OpenMP / MKL memory allocation crashes when ctranslate2 and onnxruntime coexist on Windows
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import asyncio
import base64
import io
import json
import pathlib
import wave
from typing import Optional

import av
import httpx
import numpy as np
import websockets
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from loguru import logger
from piper import PiperVoice

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
PIPECAT_HOST = os.getenv("PIPECAT_HOST", "0.0.0.0")
PIPECAT_PORT = int(os.getenv("PIPECAT_PORT", "8765"))
STT_MODEL = os.getenv("STT_MODEL", "base")
TTS_MODEL_PATH = os.getenv("TTS_MODEL_PATH", "./models/piper/en_GB-cori-high.onnx")
DEFAULT_SELLER_ID = os.getenv("SELLER_ID", "demo-seller-001")

from voice_engines import (
    DEFAULT_TTS_VOICE,
    STT_INITIAL_PROMPT,
    clean_domain_transcript,
    get_piper_voice_for,
    list_available_voices,
    split_spoken_sentences,
    synthesize_speech_chunk,
    try_handle_voice_action,
)


def _resolve_tts_model_path(raw_path: str) -> Optional[pathlib.Path]:
    """Resolve the Piper ONNX model path from CWD or project root."""
    candidate = pathlib.Path(raw_path)
    if candidate.is_file():
        return candidate
    from_root = PROJECT_ROOT / raw_path.lstrip("./\\")
    if from_root.is_file():
        return from_root
    return None


# ── Model Singletons (loaded once at startup) ──────────────────────────

_whisper_models: dict[str, WhisperModel] = {}


def get_whisper_model(model_name: str = STT_MODEL) -> WhisperModel:
    requested = model_name if model_name in ("tiny.en", "base", "base.en", "small.en") else STT_MODEL
    if requested not in _whisper_models:
        threads = 4 if requested in ("tiny.en", "small.en") else 2
        logger.info(f"Loading faster-whisper model '{requested}' (CPU, float32, threads={threads})...")
        try:
            _whisper_models[requested] = WhisperModel(
                requested,
                device="cpu",
                compute_type="float32",
                cpu_threads=threads,
                local_files_only=True,
            )
        except Exception as exc:
            if requested != "base":
                logger.warning(f"Failed to load {requested} ({exc}); falling back to 'base'")
                return get_whisper_model("base")
            raise
        logger.info(f"faster-whisper model '{requested}' ready")
    return _whisper_models[requested]


# ── Audio Processing Helpers ───────────────────────────────────────────

def decode_and_transcribe(
    raw_audio: bytes,
    stt_model: str = STT_MODEL,
    beam_size: int = 5,
    vad_silence_ms: int = 300,
) -> str:
    """Decode browser audio (WebM/Opus/WAV/Ogg) via PyAV and transcribe with faster-whisper."""
    if not raw_audio:
        return ""

    resampler = av.AudioResampler(format="flt", layout="mono", rate=16000)
    chunks: list[np.ndarray] = []

    with av.open(io.BytesIO(raw_audio)) as container:
        if not container.streams.audio:
            return ""
        for frame in container.decode(audio=0):
            for resampled in resampler.resample(frame):
                arr = resampled.to_ndarray().reshape(-1)
                if arr.size > 0:
                    chunks.append(arr)
        for resampled in resampler.resample(None):
            arr = resampled.to_ndarray().reshape(-1)
            if arr.size > 0:
                chunks.append(arr)

    if not chunks:
        return ""

    audio_np = np.concatenate(chunks).astype(np.float32)
    if audio_np.size < 3200:
        return ""
    rms = float(np.sqrt(np.mean(np.square(audio_np))))
    if rms < 0.0004:
        return ""
    peak = float(np.max(np.abs(audio_np)))
    if 0.001 < peak < 0.25:
        audio_np = audio_np * (0.5 / peak)

    model = get_whisper_model(stt_model)
    segments, _ = model.transcribe(
        audio_np,
        language="en",
        beam_size=beam_size,
        initial_prompt=STT_INITIAL_PROMPT,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": vad_silence_ms},
    )
    text = " ".join(
        seg.text.strip()
        for seg in segments
        if seg.text.strip() and getattr(seg, "no_speech_prob", 0.0) < 0.85
    )
    return clean_domain_transcript(text)


async def call_kam_agent(
    message: str,
    seller_id: str,
    conversation_id: Optional[str],
) -> dict:
    """Delegate reasoning and tool execution to the FastAPI KAM agent endpoint."""
    payload = {
        "message": message,
        "channel": "voice",
    }
    if conversation_id and conversation_id != "new":
        payload["conversation_id"] = conversation_id

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{BACKEND_URL}/api/assistant/chat",
            json=payload,
            headers={"X-Seller-Id": seller_id},
        )
        resp.raise_for_status()
        return resp.json()


# ── WebSocket Session Handler ──────────────────────────────────────────

async def handle_client(websocket):
    """Handle one browser voice WebSocket session."""
    seller_id = DEFAULT_SELLER_ID
    conversation_id: Optional[str] = None
    voice_id = DEFAULT_TTS_VOICE
    speech_rate = 1.0
    stt_model = STT_MODEL
    audio_buffer = bytearray()
    turn_seq = 0
    active_task: Optional[asyncio.Task] = None
    partial_task: Optional[asyncio.Task] = None

    logger.info("Voice WebSocket client connected")

    async def safe_send_json(obj: dict):
        try:
            await websocket.send(json.dumps(obj))
        except websockets.ConnectionClosed:
            pass

    async def send_tts_stream(spoken_text: str, my_turn: int):
        """Synthesize and stream sentence chunks sequentially so audio starts fast."""
        sentences = split_spoken_sentences(spoken_text)
        if not sentences:
            await safe_send_json({"type": "audio_unavailable"})
            return

        sent_any = False
        total = len(sentences)
        for idx, sentence in enumerate(sentences):
            if my_turn != turn_seq:
                return
            audio_bytes, mime_type, used_voice = await synthesize_speech_chunk(
                text=sentence,
                voice_id=voice_id,
                speech_rate=speech_rate,
                project_root=PROJECT_ROOT,
                default_model_path=TTS_MODEL_PATH,
            )
            if my_turn != turn_seq:
                return
            if not audio_bytes:
                continue
            await safe_send_json({
                "type": "tts_chunk_meta",
                "mime_type": mime_type,
                "sentence_index": idx,
                "total_sentences": total,
                "is_final": idx == total - 1,
                "voice_id": used_voice,
            })
            await websocket.send(audio_bytes)
            sent_any = True

        if not sent_any:
            await safe_send_json({"type": "audio_unavailable"})

    async def process_partial_audio(raw_bytes: bytes, my_turn: int):
        try:
            transcript = await asyncio.to_thread(
                decode_and_transcribe, raw_bytes, "tiny.en", 1, 200
            )
            if my_turn == turn_seq and transcript:
                await safe_send_json({"type": "partial_transcript", "text": transcript})
        except Exception:
            pass

    async def _complete_turn_with_text(user_text: str, my_turn: int):
        nonlocal conversation_id
        action_reply = await try_handle_voice_action(user_text, seller_id, BACKEND_URL)
        if my_turn != turn_seq:
            return

        if action_reply is not None:
            response_text = action_reply["response_text"]
            spoken_text = action_reply["spoken_text"]
            rec_ids = action_reply.get("recommendation_ids", [])
            action_performed = action_reply.get("action_performed")
            tool_activity = ["recommendations_api"]
            specialists_consulted = ["Operations Action Handler"]
        else:
            agent_reply = await call_kam_agent(user_text, seller_id, conversation_id)
            if my_turn != turn_seq:
                return
            if agent_reply.get("conversation_id") and agent_reply["conversation_id"] != "new":
                conversation_id = agent_reply["conversation_id"]
            response_text = agent_reply.get("response_text", "")
            spoken_text = agent_reply.get("spoken_text") or response_text
            rec_ids = agent_reply.get("recommendation_ids", [])
            action_performed = None
            tool_activity = agent_reply.get("tool_activity", [])
            specialists_consulted = agent_reply.get("specialists_consulted", [])

        await safe_send_json({
            "type": "response",
            "text": response_text,
            "spoken_text": spoken_text,
            "conversation_id": conversation_id,
            "tool_activity": tool_activity,
            "specialists_consulted": specialists_consulted,
            "recommendation_ids": rec_ids,
            "action_performed": action_performed,
        })
        await send_tts_stream(spoken_text, my_turn)

    async def process_text_turn(text_msg: str, my_turn: int):
        try:
            await _complete_turn_with_text(text_msg, my_turn)
        except Exception as exc:  # noqa: BLE001
            await safe_send_json({"type": "error", "message": str(exc)})

    async def process_audio_turn(raw_bytes: bytes, my_turn: int):
        try:
            beam = 2 if stt_model == "small.en" else 5
            transcript = await asyncio.to_thread(
                decode_and_transcribe, raw_bytes, stt_model, beam
            )
            if my_turn != turn_seq:
                return

            if not transcript:
                await safe_send_json({"type": "no_speech"})
                return

            await safe_send_json({"type": "transcript", "text": transcript})
            await _complete_turn_with_text(transcript, my_turn)

        except httpx.ConnectError:
            await safe_send_json({
                "type": "error",
                "message": f"Backend unreachable at {BACKEND_URL}",
            })
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            await safe_send_json({
                "type": "error",
                "message": f"Backend error ({exc.response.status_code}): {detail}",
            })
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error processing voice turn")
            await safe_send_json({"type": "error", "message": str(exc)})

    try:
        async for message in websocket:
            if isinstance(message, (bytes, bytearray)):
                audio_buffer.extend(message)
                continue

            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")

            if msg_type == "config":
                seller_id = data.get("seller_id") or seller_id
                conversation_id = data.get("conversation_id") or conversation_id
                if data.get("voice_id"):
                    voice_id = str(data["voice_id"])
                if data.get("speech_rate") is not None:
                    try:
                        speech_rate = max(0.75, min(1.4, float(data["speech_rate"])))
                    except (TypeError, ValueError):
                        pass
                if data.get("stt_model") in ("base", "small.en"):
                    stt_model = data["stt_model"]
                await safe_send_json({
                    "type": "ready",
                    "stt": f"faster-whisper ({stt_model})",
                    "stt_model": stt_model,
                    "tts": voice_id,
                    "tts_voice": voice_id,
                    "speech_rate": speech_rate,
                    "available_voices": list_available_voices(PROJECT_ROOT),
                })

            elif msg_type == "greet":
                greeting_text = (data.get("text") or "").strip()
                if greeting_text:
                    my_turn = turn_seq
                    await safe_send_json({"type": "greeting", "text": greeting_text})
                    if active_task and not active_task.done():
                        active_task.cancel()
                    active_task = asyncio.create_task(send_tts_stream(greeting_text, my_turn))

            elif msg_type == "text_turn":
                text_msg = (data.get("text") or "").strip()
                if text_msg:
                    turn_seq += 1
                    if active_task and not active_task.done():
                        active_task.cancel()
                    active_task = asyncio.create_task(process_text_turn(text_msg, turn_seq))

            elif msg_type == "audio_start":
                audio_buffer.clear()

            elif msg_type == "audio_partial":
                b64_data = data.get("data")
                if b64_data and (partial_task is None or partial_task.done()):
                    try:
                        raw_partial = base64.b64decode(b64_data)
                        partial_task = asyncio.create_task(
                            process_partial_audio(raw_partial, turn_seq)
                        )
                    except Exception:
                        pass

            elif msg_type == "audio_end":
                if partial_task and not partial_task.done():
                    partial_task.cancel()
                if audio_buffer:
                    raw = bytes(audio_buffer)
                    audio_buffer.clear()
                    turn_seq += 1
                    if active_task and not active_task.done():
                        active_task.cancel()
                    active_task = asyncio.create_task(process_audio_turn(raw, turn_seq))
                else:
                    await safe_send_json({"type": "no_speech"})

            elif msg_type == "interrupt":
                turn_seq += 1
                audio_buffer.clear()
                if partial_task and not partial_task.done():
                    partial_task.cancel()
                if active_task and not active_task.done():
                    active_task.cancel()
                await safe_send_json({"type": "interrupted"})

    except websockets.ConnectionClosed:
        logger.info("Voice WebSocket client disconnected")
    finally:
        if partial_task and not partial_task.done():
            partial_task.cancel()
        if active_task and not active_task.done():
            active_task.cancel()


# ── Main Entry Point ──────────────────────────────────────────────────

async def main():
    logger.info(f"Starting Virtual KAM Voice Service on ws://{PIPECAT_HOST}:{PIPECAT_PORT}")
    logger.info(f"Backend URL: {BACKEND_URL}")
    logger.info(f"STT model: faster-whisper ({STT_MODEL})")
    logger.info(f"Default TTS voice: {DEFAULT_TTS_VOICE} (offline fallback: {TTS_MODEL_PATH})")

    await asyncio.to_thread(get_whisper_model, STT_MODEL)
    await asyncio.to_thread(get_whisper_model, "tiny.en")
    await asyncio.to_thread(get_piper_voice_for, PROJECT_ROOT, TTS_MODEL_PATH)

    async with websockets.serve(
        handle_client,
        PIPECAT_HOST,
        PIPECAT_PORT,
        max_size=16 * 1024 * 1024,
    ):
        logger.info("Voice service ready — listening for browser connections")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
