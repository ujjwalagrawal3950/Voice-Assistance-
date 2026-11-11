"""Chat / agent API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_seller_id, get_db_session
from app.api.sessions import append_session_exchange
from app.agent.service import agent_service
from app.memory.store import recall_conversation_memories
from app.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    seller_id: str = Depends(get_current_seller_id),
    db: Session = Depends(get_db_session),
):
    """Send a message to the Virtual KAM agent.

    Same business logic for text and voice channels.
    """
    try:
        result = await agent_service.handle_message(
            message=payload.message,
            seller_id=seller_id,
            channel=payload.channel,
            conversation_id=payload.conversation_id,
        )
        if payload.conversation_id:
            append_session_exchange(
                db=db,
                session_id=payload.conversation_id,
                user_id=seller_id,
                user_text=payload.message,
                assistant_text=result.get("response_text", ""),
            )
        return ChatResponse(**result)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@router.get("/memory")
def get_conversation_memories(
    q: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=50),
    seller_id: str = Depends(get_current_seller_id),
):
    """Return persistent ConversationMemory records for the current seller."""
    return {
        "seller_id": seller_id,
        "memories": recall_conversation_memories(seller_id, query=q, limit=limit),
    }
