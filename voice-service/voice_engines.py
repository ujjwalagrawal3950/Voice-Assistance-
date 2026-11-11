"""Voice synthesis, STT domain helpers, and voice-action utilities."""

from __future__ import annotations

import asyncio
import io
import logging
import os
import pathlib
import re
import wave
from typing import Any, Optional

import edge_tts
import httpx
from piper import PiperVoice
from piper.config import SynthesisConfig

logger = logging.getLogger("voice-service.engines")

DEFAULT_TTS_VOICE = os.getenv("TTS_VOICE", "en-IN-NeerjaExpressiveNeural")

STT_INITIAL_PROMPT = (
    "Snapdeal seller business consultation. Sales, orders, revenue, "
    "cancellation rate, average selling price ASP, out of stock, SKU, "
    "inventory, visibility, restock, rupees, lakhs, crores, pickup SLA."
)

TTS_VOICE_CATALOG: list[dict[str, str]] = [
    {
        "id": "en-IN-NeerjaExpressiveNeural",
        "label": "Neerja (Indian English • Expressive)",
        "engine": "edge-tts",
        "edge_voice": "en-IN-NeerjaExpressiveNeural",
    },
    {
        "id": "en-IN-PrabhatNeural",
        "label": "Prabhat (Indian English Male • Neural)",
        "engine": "edge-tts",
        "edge_voice": "en-IN-PrabhatNeural",
    },
    {
        "id": "en-US-AvaMultilingualNeural",
        "label": "Ava (Conversational • Expressive)",
        "engine": "edge-tts",
        "edge_voice": "en-US-AvaMultilingualNeural",
    },
    {
        "id": "en-GB-SoniaNeural",
        "label": "Sonia (British English • Neural)",
        "engine": "edge-tts",
        "edge_voice": "en-GB-SoniaNeural",
    },
    {
        "id": "offline-cori",
        "label": "Cori HD (Offline Local)",
        "engine": "piper",
        "model_rel": "./models/piper/en_GB-cori-high.onnx",
    },
    {
        "id": "offline-jenny",
        "label": "Jenny (Offline Local)",
        "engine": "piper",
        "model_rel": "./models/piper/en_GB-jenny_dioco-medium.onnx",
    },
    {
        "id": "offline-lessac",
        "label": "Lessac (Offline US)",
        "engine": "piper",
        "model_rel": "./models/piper/en_US-lessac-medium.onnx",
    },
]

_VOICE_BY_ID: dict[str, dict[str, str]] = {entry["id"]: entry for entry in TTS_VOICE_CATALOG}
_piper_cache: dict[str, PiperVoice] = {}


def _resolve_model_path(project_root: pathlib.Path, rel_or_abs: str) -> pathlib.Path:
    p = pathlib.Path(rel_or_abs)
    return p if p.is_absolute() else (project_root / p).resolve()


def list_available_voices(project_root: pathlib.Path) -> list[dict[str, str]]:
    """Return voices supported on this machine (always includes edge-tts + existing Piper models)."""
    available: list[dict[str, str]] = []
    for entry in TTS_VOICE_CATALOG:
        if entry["engine"] == "piper":
            model_path = _resolve_model_path(project_root, entry["model_rel"])
            if not model_path.exists():
                continue
        available.append({
            "id": entry["id"],
            "label": entry["label"],
            "engine": entry["engine"],
        })
    return available


def _pick_offline_piper_path(
    project_root: pathlib.Path,
    default_model_path: str,
    requested_voice_id: Optional[str] = None,
) -> tuple[str, pathlib.Path]:
    """Select requested Piper model or best available clear offline model."""
    if requested_voice_id and requested_voice_id in _VOICE_BY_ID:
        entry = _VOICE_BY_ID[requested_voice_id]
        if entry["engine"] == "piper":
            candidate = _resolve_model_path(project_root, entry["model_rel"])
            if candidate.exists():
                return entry["id"], candidate

    for preferred_id in ("offline-cori", "offline-jenny", "offline-lessac"):
        entry = _VOICE_BY_ID[preferred_id]
        candidate = _resolve_model_path(project_root, entry["model_rel"])
        if candidate.exists():
            return entry["id"], candidate

    fallback = _resolve_model_path(project_root, default_model_path)
    return "offline-default", fallback


def get_piper_voice_for(
    project_root: pathlib.Path,
    default_model_path: str,
    requested_voice_id: Optional[str] = None,
) -> tuple[str, PiperVoice]:
    """Load and cache a PiperVoice instance cleanly."""
    voice_id, model_path = _pick_offline_piper_path(project_root, default_model_path, requested_voice_id)
    key = str(model_path)
    if key not in _piper_cache:
        if not model_path.exists():
            raise FileNotFoundError(f"Piper model not found: {model_path}")
        logger.info("Loading Piper offline voice %s from %s", voice_id, model_path.name)
        _piper_cache[key] = PiperVoice.load(str(model_path))
    return voice_id, _piper_cache[key]


def _format_indian_rupees(amount_str: str, unit_suffix: str = "") -> str:
    sign = ""
    raw = amount_str.strip()
    if raw.startswith("-"):
        sign = "minus "
        raw = raw[1:].strip()
    elif raw.startswith("+"):
        raw = raw[1:].strip()
    numeric_clean = raw.replace(",", "")
    suffix_lower = unit_suffix.strip().lower()
    if suffix_lower in ("l", "lac", "lakh", "lakhs"):
        return f"{sign}{numeric_clean} lakh rupees"
    if suffix_lower in ("cr", "crore", "crores"):
        return f"{sign}{numeric_clean} crore rupees"
    if suffix_lower == "k":
        try:
            val = float(numeric_clean) * 1000
            numeric_clean = str(int(val)) if val.is_integer() else f"{val:.0f}"
        except ValueError:
            return f"{sign}{numeric_clean} thousand rupees"

    if "." in numeric_clean:
        try:
            val = float(numeric_clean)
        except ValueError:
            return f"{sign}{numeric_clean} rupees"
        if val >= 10_000_000:
            return f"{sign}{val / 10_000_000:.2f}".rstrip("0").rstrip(".") + " crore rupees"
        if val >= 100_000:
            return f"{sign}{val / 100_000:.2f}".rstrip("0").rstrip(".") + " lakh rupees"
        return f"{sign}{val:g} rupees"

    try:
        amount = int(numeric_clean)
    except ValueError:
        return f"{sign}{numeric_clean} rupees"

    parts: list[str] = []
    if amount >= 10_000_000:
        crores, amount = divmod(amount, 10_000_000)
        parts.append(f"{crores} crore")
    if amount >= 100_000:
        lakhs, amount = divmod(amount, 100_000)
        parts.append(f"{lakhs} lakh")
    if amount >= 1_000 and (parts or (amount >= 10_000 and amount % 1_000 == 0)):
        thousands, amount = divmod(amount, 1_000)
        parts.append(f"{thousands} thousand")
    if amount > 0 or not parts:
        parts.append(str(amount))
    return f"{sign}{' '.join(parts)} rupees"


def normalize_tts_text(text: str) -> str:
    """Ensure fallback greetings or non-backend strings also read Indian numbers cleanly."""
    clean = re.sub(r"[*_`#]+", "", text)
    clean = re.sub(r"^\s*[-•]\s+", "", clean, flags=re.MULTILINE)
    currency_pattern = re.compile(
        r"(?:₹|Rs\.?\s*|INR\s*)([+-]?\s*\d+(?:,\d+)*(?:\.\d+)?)(?:\s*(crores?|cr|lakhs?|lac|l|k)\b)?",
        re.IGNORECASE,
    )
    clean = currency_pattern.sub(
        lambda m: _format_indian_rupees(m.group(1), m.group(2) or ""),
        clean,
    )
    clean = clean.replace("→", " to ").replace("->", " to ")
    clean = clean.replace("≥", "at least ").replace("≤", "up to ")
    clean = clean.replace("—", ", ").replace("–", ", ")
    clean = re.sub(r"~(?=\d)", "about ", clean)
    clean = re.sub(
        r"([+-])\s*(\d+(?:\.\d+)?)\s*%",
        lambda m: ("minus " if m.group(1) == "-" else "") + f"{m.group(2)} percent",
        clean,
    )
    clean = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"\1 percent", clean)
    clean = re.sub(r"\bOOS\b", "out of stock", clean)
    clean = re.sub(r"\bASP\b", "average selling price", clean)
    clean = re.sub(r"\bSLAs\b", "pickup timelines", clean)
    clean = re.sub(r"\bSLA\b", "pickup timeline", clean)
    clean = re.sub(r"\bSKUs\b(?!-)", "products", clean)
    clean = re.sub(r"\bSKU\b(?!-)", "product", clean)
    clean = re.sub(r"[^\x20-\x7E]", " ", clean)
    clean = re.sub(r"\s+([,.;!?])", r"\1", clean)
    return re.sub(r"\s+", " ", clean).strip()


def split_spoken_sentences(text: str) -> list[str]:
    """Split spoken reply into smooth, natural TTS chunks for streaming playback."""
    clean = normalize_tts_text(text)
    if not clean:
        return []
    raw_parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", clean) if p.strip()]
    merged: list[str] = []
    for part in raw_parts:
        if merged and len(part) < 28 and len(merged[-1]) + len(part) < 220:
            merged[-1] = f"{merged[-1]} {part}"
        else:
            merged.append(part)
    return merged


def clean_domain_transcript(text: str) -> str:
    """Fix common high-confidence Indian-English ASR homophones on Snapdeal domain terms."""
    if not text:
        return ""
    fixed = re.sub(r"\bsnap\s*deal\b", "Snapdeal", text, flags=re.IGNORECASE)
    fixed = re.sub(
        r"\b(my|our|total|monthly|weekly|gross|net)\s+sails\b",
        r"\1 sales",
        fixed,
        flags=re.IGNORECASE,
    )
    fixed = re.sub(
        r"\bsails\s+(down|up|drop|dropped|fell|grew|today|this|last|are|were)\b",
        r"sales \1",
        fixed,
        flags=re.IGNORECASE,
    )
    return fixed.strip()


def _clamp_rate(rate: float) -> float:
    return max(0.75, min(1.4, float(rate)))


def synthesize_piper_sync(
    text: str,
    project_root: pathlib.Path,
    default_model_path: str,
    voice_id: Optional[str] = None,
    speech_rate: float = 1.0,
) -> tuple[bytes, str, str]:
    """Synthesize clean WAV using local Piper with tuned clarity parameters."""
    actual_id, voice = get_piper_voice_for(project_root, default_model_path, voice_id)
    clamped_rate = _clamp_rate(speech_rate)
    # 1.06 base length_scale adds crisp articulation without sounding sluggish
    syn_cfg = SynthesisConfig(
        length_scale=round(1.06 / clamped_rate, 3),
        noise_scale=0.5,
        noise_w_scale=0.65,
    )
    buf = io.BytesIO()
    wf = wave.open(buf, "wb")
    try:
        voice.synthesize_wav(text, wf, syn_config=syn_cfg)
    finally:
        wf.close()
    return buf.getvalue(), "audio/wav", actual_id


async def _synthesize_edge_mp3(text: str, edge_voice: str, speech_rate: float) -> bytes:
    clamped_rate = _clamp_rate(speech_rate)
    pct = round((clamped_rate - 1.0) * 100)
    rate_str = f"{pct:+d}%"
    comm = edge_tts.Communicate(text=text, voice=edge_voice, rate=rate_str)

    async def _collect() -> bytes:
        chunks = [c["data"] async for c in comm.stream() if c.get("type") == "audio" and c.get("data")]
        return b"".join(chunks)

    audio = await asyncio.wait_for(_collect(), timeout=12.0)
    if not audio:
        raise RuntimeError(f"Empty audio stream returned by edge-tts ({edge_voice})")
    return audio


async def synthesize_speech_chunk(
    text: str,
    voice_id: str,
    speech_rate: float,
    project_root: pathlib.Path,
    default_model_path: str,
) -> tuple[bytes, str, str]:
    """Synthesize text using selected neural/offline voice with automatic offline Piper fallback."""
    clean_text = normalize_tts_text(text)
    if not clean_text:
        return b"", "audio/wav", voice_id

    entry = _VOICE_BY_ID.get(voice_id) or _VOICE_BY_ID.get(DEFAULT_TTS_VOICE)
    if entry and entry["engine"] == "edge-tts":
        try:
            mp3_bytes = await _synthesize_edge_mp3(clean_text, entry["edge_voice"], speech_rate)
            return mp3_bytes, "audio/mpeg", entry["id"]
        except Exception as exc:
            logger.warning("Neural TTS (%s) failed (%s); falling back to offline Piper.", entry["id"], exc)

    requested_piper = entry["id"] if (entry and entry["engine"] == "piper") else None
    return await asyncio.to_thread(
        synthesize_piper_sync,
        clean_text,
        project_root,
        default_model_path,
        requested_piper,
        speech_rate,
    )


def _match_target_recommendations(
    text_lower: str,
    pending: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], bool]:
    """Resolve explicit ordinal, ID, or keyword references to pending recommendations.

    Returns `(matched_items, needs_clarification)`.
    """
    if not pending:
        return [], False

    # Explicit rec-id match
    id_matches = [r for r in pending if r.get("id", "").lower() in text_lower]
    if id_matches:
        return id_matches, False

    if re.search(r"\b(all|every|both|everything)\b", text_lower):
        return pending, False

    ordinals = [
        (r"\b(first|1st|number\s+one|recommendation\s+1|one)\b", 0),
        (r"\b(second|2nd|number\s+two|recommendation\s+2|two)\b", 1),
        (r"\b(third|3rd|number\s+three|recommendation\s+3|three)\b", 2),
    ]
    for pattern, idx in ordinals:
        if re.search(pattern, text_lower) and idx < len(pending):
            return [pending[idx]], False

    # Keyword match against title / suggested_action
    keywords = ("restock", "stock", "inventory", "cancel", "pickup", "sla", "visibility", "campaign", "ad")
    mentioned_kw = [kw for kw in keywords if kw in text_lower]
    if mentioned_kw:
        kw_matches = [
            r for r in pending
            if any(
                kw in (r.get("title", "") + " " + r.get("suggested_action", "")).lower()
                for kw in mentioned_kw
            )
        ]
        if len(kw_matches) == 1:
            return kw_matches, False

    if len(pending) == 1:
        return [pending[0]], False

    return [], True


async def try_handle_voice_action(
    transcript: str,
    seller_id: str,
    backend_url: str,
) -> Optional[dict[str, Any]]:
    """Detect and execute real recommendation actions from spoken/typed voice commands."""
    text_lower = transcript.strip().lower()
    if not text_lower:
        return None

    is_list_cmd = bool(
        re.search(
            r"\b(list|show|what are|read|check)\b.*\b(recommendations?|actions?|pending)\b",
            text_lower,
        )
    )
    is_approve = bool(
        re.search(
            r"\b(approve|accept|confirm|go ahead with|execute|yes approve)\b",
            text_lower,
        )
    )
    is_reject = bool(re.search(r"\b(reject|decline|dismiss|skip)\b", text_lower))

    mentions_rec_context = bool(
        re.search(
            r"\b(recommendation|recommendations|rec-\d+|restock|inventory|cancellation|visibility|first one|second one|all pending|pending action)\b",
            text_lower,
        )
    )

    if not is_list_cmd:
        if not ((is_approve or is_reject) and mentions_rec_context):
            return None
        # Never execute state mutations on advisory questions or negations ("Should I approve...", "Don't reject...").
        if text_lower.endswith("?") or re.search(
            r"\b(?:should i|can i|could i|would you|why|how|when|don't|do not|never|before i|if i)\b",
            text_lower,
        ):
            return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{backend_url}/api/recommendations",
                params={"seller_id": seller_id},
            )
            if resp.status_code != 200:
                return None
            all_recs: list[dict[str, Any]] = resp.json()
    except Exception as exc:
        logger.warning("Voice action failed to query recommendations: %s", exc)
        return None

    pending = [
        r for r in all_recs
        if r.get("approval_status") in ("new", "viewed", "pending")
    ]

    if is_list_cmd:
        if not pending:
            msg = "You have no pending recommendations right now. All previous action items have already been reviewed."
            return {
                "response_text": msg,
                "spoken_text": msg,
                "intent": "recommendations_list",
                "recommendation_ids": [],
                "action_performed": None,
            }
        lines = [f"{i + 1}. {r['title']} ({r.get('urgency', 'medium')} urgency)" for i, r in enumerate(pending[:3])]
        spoken_items = "; ".join(f"number {i + 1}, {r['title']}" for i, r in enumerate(pending[:3]))
        msg = f"You have {len(pending)} pending recommendations:\n" + "\n".join(lines)
        spoken = f"You have {len(pending)} pending recommendations: {spoken_items}. Say approve recommendation 1, 2, or 3 whenever you're ready."
        return {
            "response_text": msg,
            "spoken_text": spoken,
            "intent": "recommendations_list",
            "recommendation_ids": [r["id"] for r in pending[:3]],
            "action_performed": None,
        }

    action = "approve" if is_approve else "reject"
    if not pending:
        msg = "There are no pending recommendations left to update."
        return {
            "response_text": msg,
            "spoken_text": msg,
            "intent": "recommendation_action",
            "recommendation_ids": [],
            "action_performed": None,
        }

    targets, needs_clarification = _match_target_recommendations(text_lower, pending)
    if needs_clarification or not targets:
        summary = ", ".join(f"number {i + 1} is {r['title']}" for i, r in enumerate(pending[:3]))
        spoken = f"You have {len(pending)} pending recommendations: {summary}. Which one would you like me to {action}?"
        return {
            "response_text": spoken,
            "spoken_text": spoken,
            "intent": "recommendation_clarify",
            "recommendation_ids": [r["id"] for r in pending[:3]],
            "action_performed": None,
        }

    updated: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        for rec in targets:
            res = await client.post(
                f"{backend_url}/api/recommendations/{rec['id']}/approve",
                params={"seller_id": seller_id},
                json={"action": action, "notes": "Updated via AI Voice KAM"},
            )
            if res.status_code == 200:
                updated.append(res.json())

    if not updated:
        return None

    titles = ", ".join(r["title"] for r in updated)
    past = "approved" if action == "approve" else "rejected"
    msg = f"Done! I have {past} {len(updated)} recommendation(s): {titles}."
    spoken = f"Done. I have {past} {titles} on your dashboard."
    return {
        "response_text": msg,
        "spoken_text": spoken,
        "intent": "recommendation_action",
        "recommendation_ids": [r["id"] for r in updated],
        "action_performed": {
            "action": past,
            "recommendations": updated,
        },
    }
