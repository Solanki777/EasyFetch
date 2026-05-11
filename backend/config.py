from __future__ import annotations
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_version: str = "1.0.0"
    debug: bool = False

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_provider: str = "groq"          # groq | gemini | openai
    groq_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    llm_model: str = "llama3-8b-8192"
    llm_temperature: float = 0.0
    llm_timeout_seconds: float = 15.0

    # ── Google Drive ──────────────────────────────────────────────────────────
    google_service_account_json: str = "credentials/service_account.json"
    google_drive_root_folder_id: str = ""   # optional: scope all searches to this folder

    # ── Session ───────────────────────────────────────────────────────────────
    session_ttl_seconds: int = 3600
    max_session_history: int = 20

    # ── Search ────────────────────────────────────────────────────────────────
    max_drive_results: int = 50
    default_result_limit: int = 10

    # ── CORS ──────────────────────────────────────────────────────────────────
    cors_origins: List[str] = ["http://localhost:8501", "http://localhost:3000"]

    # ── Redis (optional) ──────────────────────────────────────────────────────
    redis_url: str = ""


settings = Settings()
