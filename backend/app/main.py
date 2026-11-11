"""FastAPI application entry point."""

from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    alerts,
    analytics,
    calendar,
    chat,
    dashboard,
    forecast,
    health,
    inventory,
    products,
    recommendations,
    seller,
    sessions,
    voice,
)
from app.config import settings
from app.database import SessionLocal, create_db_and_tables
from app.models import Seller
from app.services.intelligence import generate_proactive_alerts


def _validate_config() -> None:
    """Validate required configuration at startup."""
    errors = []

    if not settings.secret_key or settings.secret_key == "replace-with-a-secure-random-key":
        errors.append("SECRET_KEY must be set to a secure random key")

    # # Local Ollama validation (temporarily commented out while using Google Gemini API)
    # if not settings.ollama_base_url:
    #     errors.append("OLLAMA_BASE_URL is required")
    #
    # if not settings.ollama_model:
    #     errors.append("OLLAMA_MODEL is required")

    if not settings.google_model:
        errors.append("GOOGLE_MODEL is required")

    if not settings.google_base_url:
        errors.append("GOOGLE_BASE_URL is required")

    if settings.app_env == "production" and not settings.google_api_key.strip():
        errors.append("GOOGLE_API_KEY is required in production")

    if not settings.database_url:
        errors.append("DATABASE_URL is required")

    if errors:
        formatted = "\n  - " + "\n  - ".join(errors)
        raise RuntimeError(f"Configuration validation failed:{formatted}")


async def _proactive_digest_loop() -> None:
    """Periodic background job running proactive diagnosis for all sellers."""
    await asyncio.sleep(5.0)
    while True:
        try:
            def _run_once():
                db = SessionLocal()
                try:
                    seller_ids = [s.id for s in db.query(Seller.id).all()]
                    for sid in seller_ids:
                        generate_proactive_alerts(db, sid, channel="digest", persist=True)
                finally:
                    db.close()

            await asyncio.to_thread(_run_once)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(6 * 3600)


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        _validate_config()
        create_db_and_tables()
        digest_task = asyncio.create_task(_proactive_digest_loop())
        try:
            yield
        finally:
            digest_task.cancel()

    app = FastAPI(
        title="Virtual KAM API",
        description="AI-powered Virtual Key Account Manager for Indian marketplace sellers",
        version="0.1.0",
        debug=settings.app_debug,
        lifespan=lifespan,
    )

    # CORS - Allow frontend dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
        ],
        allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$" if settings.app_debug else None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(seller.router)
    app.include_router(dashboard.router)
    app.include_router(products.router)
    app.include_router(chat.router)
    app.include_router(forecast.router)
    app.include_router(inventory.router)
    app.include_router(analytics.router)
    app.include_router(calendar.router)
    app.include_router(recommendations.router)
    app.include_router(alerts.router)
    app.include_router(sessions.router)
    app.include_router(health.router)
    app.include_router(voice.router)

    @app.get("/health")
    def health_simple():
        return {"status": "ok", "app_env": settings.app_env}

    return app


app = create_app()
