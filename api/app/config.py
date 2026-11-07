from functools import lru_cache
from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ROOT_DIR = _BACKEND_DIR.parent
_ENV_FILES = (
    str(_BACKEND_DIR / ".env"),
    str(_ROOT_DIR / ".env"),
    ".env",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./meetingmind.db"
    jwt_secret: str = "dev-only-change-me"
    jwt_expire_minutes: int = 1440
    cors_origins: str = "http://localhost:5173"

    hindsight_api_url: str = "http://localhost:8888"
    hindsight_api_key: str | None = None
    hindsight_bank_prefix: str = "meetingmind"

    llm_provider: str = "groq"
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: str | None = None
    llm_model: str = "openai/gpt-oss-20b"

    max_upload_mb: int = 2

    @model_validator(mode="after")
    def resolve_hindsight_settings(self):
        # Remove accidental localhost:8888 fallback when Cloud is configured (API key provided or Cloud URL set)
        if self.hindsight_api_key and (
            not self.hindsight_api_url
            or self.hindsight_api_url in ("http://localhost:8888", "http://127.0.0.1:8888", "localhost:8888")
        ):
            self.hindsight_api_url = "https://api.hindsight.vectorize.io"

        # Ensure scheme is present
        if self.hindsight_api_url and not self.hindsight_api_url.startswith(("http://", "https://")):
            self.hindsight_api_url = f"https://{self.hindsight_api_url}"

        # Strip trailing slash
        if self.hindsight_api_url:
            self.hindsight_api_url = self.hindsight_api_url.rstrip("/")

        return self

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
