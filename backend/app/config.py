"""Application configuration using pydantic-settings.

Values are loaded from environment variables. See .env.example for the
documented set of variables. Secret values are never committed.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    secret_key: str = Field(default="replace-with-a-secure-random-key", alias="SECRET_KEY")
    seller_id: str = Field(default="demo-seller-001", alias="SELLER_ID")

    # Database
    database_url: str = Field(default="sqlite:///./virtual_kam.db", alias="DATABASE_URL")

    # # Ollama (local LLM — temporarily commented out in favor of Google Gemini API)
    # ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    # ollama_model: str = Field(default="llama3.1:8b", alias="OLLAMA_MODEL")

    # Online LLM API (Google Gemini — loaded from .env GOOGLE_API_KEY, server-side only)
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    google_model: str = Field(default="gemini-3-flash-preview", alias="GOOGLE_MODEL")
    google_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta",
        alias="GOOGLE_BASE_URL",
    )

    # Voice (STT/TTS providers — local by default)
    stt_provider: str = Field(default="faster_whisper", alias="STT_PROVIDER")
    stt_model: str = Field(default="base", alias="STT_MODEL")
    tts_provider: str = Field(default="piper", alias="TTS_PROVIDER")
    tts_model_path: str = Field(default="./models/piper/en_US-lessac-medium.onnx", alias="TTS_MODEL_PATH")
    voice_transport: str = Field(default="webrtc", alias="VOICE_TRANSPORT")

    # Pipecat
    pipecat_host: str = Field(default="0.0.0.0", alias="PIPECAT_HOST")
    pipecat_port: int = Field(default=8765, alias="PIPECAT_PORT")

    model_config = {
        "env_file": (".env", "../.env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


settings = Settings()
