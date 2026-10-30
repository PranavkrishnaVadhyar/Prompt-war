from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent


class Settings(BaseSettings):
    database_url: str
    supabase_url: str
    supabase_service_role_key: str
    supabase_publishable_key: str = ""
    frontend_origins: str = "http://127.0.0.1:8000,http://localhost:8000"
    cookie_secure: bool = False
    max_submission_bytes: int = Field(default=262144, ge=1024, le=1048576)
    auth_ip_limit: int = Field(default=300, ge=20, le=5000)
    auth_email_limit: int = Field(default=10, ge=3, le=50)
    groq_api_key: str = ""
    groq_eval_models: str = ""
    openai_api_key: str = ""
    openai_eval_model: str = "gpt-4.1-mini"
    evaluation_workers: int = Field(default=2, ge=1, le=4)
    evaluation_timeout: int = Field(default=60, ge=15, le=120)
    model_config = SettingsConfigDict(env_file=BACKEND / ".env", extra="ignore", env_file_encoding="utf-8")

    @property
    def postgres_url(self):
        raw = self.database_url.replace("postgresql+asyncpg://", "postgresql://", 1).replace("postgresql+psycopg://", "postgresql://", 1)
        parts = urlsplit(raw)
        query = [("sslmode" if key == "ssl" else key,value) for key,value in parse_qsl(parts.query,keep_blank_values=True)]
        return urlunsplit((parts.scheme,parts.netloc,parts.path,urlencode(query),parts.fragment))

    @property
    def origins(self):
        return [v.strip().rstrip("/") for v in self.frontend_origins.split(",") if v.strip()]

    @property
    def auth_key(self):
        return self.supabase_publishable_key or self.supabase_service_role_key


@lru_cache
def settings():
    return Settings()

