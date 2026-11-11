"""Health check endpoints with dependency verification.

Checks backend database and LLM connectivity (currently Google Gemini API;
local Ollama check is preserved cleanly in comments below).
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.config import settings

router = APIRouter(prefix="/health", tags=["health"])


def _check_database(db: Session) -> dict:
    """Verify database connectivity by running a trivial query."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "detail": "database reachable"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "detail": f"database unreachable: {exc}"}


# # Local Ollama health check (temporarily commented out while using Google Gemini API)
# def _check_ollama() -> dict:
#     """Verify Ollama is reachable and the configured model exists."""
#     try:
#         import httpx
#
#         with httpx.Client(timeout=5.0) as client:
#             resp = client.get(f"{settings.ollama_base_url}/api/tags")
#             if resp.status_code != 200:
#                 return {
#                     "status": "error",
#                     "detail": f"Ollama returned HTTP {resp.status_code}",
#                 }
#             models = [m.get("name", "") for m in resp.json().get("models", [])]
#             if settings.ollama_model in models:
#                 return {
#                     "status": "ok",
#                     "detail": f"Ollama reachable, model {settings.ollama_model} available",
#                 }
#             return {
#                 "status": "warning",
#                 "detail": f"Ollama reachable but model {settings.ollama_model} not found",
#                 "available_models": models,
#             }
#     except httpx.ConnectError:
#         return {
#             "status": "error",
#             "detail": f"Ollama unreachable at {settings.ollama_base_url}",
#         }
#     except Exception as exc:  # noqa: BLE001
#         return {"status": "error", "detail": f"Ollama check failed: {exc}"}


def _check_google_llm() -> dict:
    """Verify Google Gemini API configuration and connectivity."""
    key = (settings.google_api_key or "").strip()
    if not key or key.lower().startswith("your-"):
        return {
            "status": "warning",
            "detail": "GOOGLE_API_KEY is not configured in .env",
        }
    try:
        import httpx

        base_url = settings.google_base_url.rstrip("/")
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(
                f"{base_url}/models",
                headers={"x-goog-api-key": key},
            )
            if resp.status_code == 200:
                return {
                    "status": "ok",
                    "detail": f"Google Gemini API reachable (model: {settings.google_model})",
                }
            if resp.status_code in (400, 401, 403):
                return {
                    "status": "error",
                    "detail": "GOOGLE_API_KEY rejected by Google Gemini API",
                }
            return {
                "status": "warning",
                "detail": f"Google Gemini API returned HTTP {resp.status_code}",
            }
    except httpx.ConnectError:
        return {
            "status": "error",
            "detail": f"Google Gemini API unreachable at {settings.google_base_url}",
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "detail": f"Google Gemini check failed: {exc}"}


@router.get("")
def health(response: Response, db: Session = Depends(get_db_session)):
    """Aggregated health status for all dependencies.

    Returns HTTP 200 when all dependencies are healthy, 503 when any
    critical dependency is unavailable.
    """
    db_status = _check_database(db)
    # ollama_status = _check_ollama()
    google_status = _check_google_llm()

    dependencies = {
        "database": db_status,
        # "ollama": ollama_status,
        "google": google_status,
    }

    overall = "ok"
    for dep in dependencies.values():
        if dep["status"] == "error":
            overall = "error"
        elif dep["status"] == "warning" and overall == "ok":
            overall = "warning"

    if overall == "error":
        response.status_code = 503

    return {
        "status": overall,
        "app_env": settings.app_env,
        "dependencies": dependencies,
    }
