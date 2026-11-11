"""Memory configuration — pydantic settings for the memory module.

Environment variables (all prefixed with MEMORY_):

MEMORY_ENABLED                  bool   default true
MEMORY_BACKEND                  str    in_memory | vector (default: in_memory)
MEMORY_RECALL_TIMEOUT_MS        int    default 1200
MEMORY_TOP_K                    int    default 5
MEMORY_CAPTURE_MODE             str    facts_only | full_turn | off  (default: facts_only)
MEMORY_SUMMARIZE_ENABLED        bool   default true
MEMORY_SUMMARIZE_TRIGGER_TOKENS int    default 3000
MEMORY_SUMMARIZE_TARGET_TOKENS  int    default 1500
MEMORY_PREFETCH                 bool   default true
MEMORY_RETENTION_DAYS           int    default 30
MEMORY_MAX_STORED_PER_SELLER    int    default 1000
"""

from pydantic import BaseModel, Field, field_validator


class MemorySettings(BaseModel):
    """Memory service configuration."""

    enabled: bool = Field(default=True, alias="MEMORY_ENABLED")
    backend: str = Field(default="in_memory", alias="MEMORY_BACKEND")
    recall_timeout_ms: int = Field(default=1200, alias="MEMORY_RECALL_TIMEOUT_MS")
    top_k: int = Field(default=5, alias="MEMORY_TOP_K")
    capture_mode: str = Field(default="facts_only", alias="MEMORY_CAPTURE_MODE")
    summarize_enabled: bool = Field(default=True, alias="MEMORY_SUMMARIZE_ENABLED")
    summarize_trigger_tokens: int = Field(default=3000, alias="MEMORY_SUMMARIZE_TRIGGER_TOKENS")
    summarize_target_tokens: int = Field(default=1500, alias="MEMORY_SUMMARIZE_TARGET_TOKENS")
    prefetch: bool = Field(default=True, alias="MEMORY_PREFETCH")
    retention_days: int = Field(default=30, alias="MEMORY_RETENTION_DAYS")
    max_stored_per_seller: int = Field(default=1000, alias="MEMORY_MAX_STORED_PER_SELLER")

    @field_validator("backend")
    @classmethod
    def _validate_backend(cls, v: str) -> str:
        v = v.lower()
        if v not in ("in_memory", "vector"):
            raise ValueError(f"Unknown memory backend: {v}. Use 'in_memory' or 'vector'.")
        return v

    @field_validator("capture_mode")
    @classmethod
    def _validate_capture_mode(cls, v: str) -> str:
        v = v.lower()
        if v not in ("facts_only", "full_turn", "off"):
            raise ValueError(
                f"Unknown memory capture mode: {v}. Use 'facts_only', 'full_turn', or 'off'."
            )
        return v

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }


class MemorySettingsError(Exception):
    """Raised when memory configuration is invalid."""

    pass


def load_settings() -> MemorySettings:
    """Load memory settings from environment variables."""
    try:
        return MemorySettings()
    except Exception as exc:  # pydantic.ValidationError
        raise MemorySettingsError(f"Invalid memory configuration: {exc}") from exc


memory_settings = MemorySettings()
