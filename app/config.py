from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_fast_model: str = "openai/gpt-oss-20b"
    groq_reasoning_effort: str = "low"  # low | medium | high (gpt-oss models only)

    database_url: str = "sqlite:///./data/app.db"
    chroma_dir: str = "./data/chroma"
    secret_key: str = "dev-secret-change-me"
    access_token_minutes: int = 720

    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 5
    quality_threshold: float = 7.0
    max_revisions: int = 1
    max_upload_mb: int = 10

    cost_per_m_input: float = 0.15
    cost_per_m_output: float = 0.60


@lru_cache
def get_settings() -> Settings:
    return Settings()
