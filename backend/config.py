from typing import List, Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        enable_decoding=False
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_version: str = "1.0.0"
    debug: bool = False

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_provider: str = "groq"   # groq | gemini | openai

    groq_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""

    llm_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.0
    llm_timeout_seconds: float = 15.0

    # ── Google Drive ────────────────────────────────────────────────────────
    google_drive_root_folder_id: str = ""

    # ── Session ─────────────────────────────────────────────────────────────
    session_ttl_seconds: int = 3600
    max_session_history: int = 20

    # ── Search ──────────────────────────────────────────────────────────────
    max_drive_results: int = 50
    default_result_limit: int = 10

    # ── CORS ────────────────────────────────────────────────────────────────
    cors_origins: List[str] = [
        "http://localhost:8501",
        "http://localhost:3000",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]

        if isinstance(v, list):
            return v

        return ["http://localhost:8501"]

    # ── Redis ───────────────────────────────────────────────────────────────
    redis_url: str = ""


settings = Settings()
