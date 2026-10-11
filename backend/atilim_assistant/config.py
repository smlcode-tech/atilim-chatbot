"""Ortam değişkenlerinden ve backend/.env dosyasından okunan uygulama ayarları."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_ROOT / ".env", extra="ignore")

    gemini_api_key: SecretStr
    llm_model: str = "gemini-3.8-flash"
    embed_model: str = "gemini-embedding-001"
    embed_dimensions: int = 768

    data_dir: Path = BACKEND_ROOT / "data"
    collection: str = "atilim_documents"
    retrieval_top_k: int = 6

    api_host: str = "127.0.0.1"
    api_port: int = 8000

    @property
    def vector_store_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def prepared_answers_path(self) -> Path:
        return self.data_dir / "prepared_answers.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
