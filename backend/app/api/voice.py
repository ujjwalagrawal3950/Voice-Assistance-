"""Voice session API endpoints."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
import uuid

from app.api.deps import get_current_seller_id
from app.config import settings


class VoiceSessionResponse(BaseModel):
    session_id: str
    pipecat_ws_url: str
    seller_id: str


router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/session", response_model=VoiceSessionResponse)
def create_voice_session(
    request: Request,
    seller_id: str = Depends(get_current_seller_id),
):
    """Create a voice session for the authenticated seller.

    Returns a session ID and voice WebSocket URL. The browser connects
    to this WebSocket for real-time audio streaming with the voice
    service (running separately on Python 3.13).

    The voice service URL and any STT/TTS credentials are held server-side only.
    The browser never receives Ollama URLs or provider credentials.
    """
    session_id = str(uuid.uuid4())
    forwarded_host = request.headers.get("x-forwarded-host")
    host = forwarded_host.split(":")[0] if forwarded_host else "localhost"
    return {
        "session_id": session_id,
        "pipecat_ws_url": f"ws://{host}:{settings.pipecat_port}",
        "seller_id": seller_id,
    }
