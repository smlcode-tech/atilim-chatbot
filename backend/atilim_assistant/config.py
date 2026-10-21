"""Ortam değişkenlerinden ve backend/.env dosyasından okunan uygulama ayarları."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_ROOT / ".env", extra="ignore")

    groq_api_key: SecretStr
    voyage_api_key: SecretStr
    llm_model: str = "openai/gpt-oss-120b"
    embed_model: str = "voyage-multilingual-2"

    data_dir: Path = BACKEND_ROOT / "data"
    collection: str = "atilim_documents"
    retrieval_top_k: int = 6
    # Modele verilen bağlamın karakter sınırı. Groq ücretsiz katmanı dakikada 8000 token kabul
    # eder; Türkçe metinde bu bütçe yaklaşık 2500 token tutar, soru ve yanıta yer kalır.
    retrieval_max_chars: int = 8000

    # Kota bittiğinde modelin yeniden denenmeden önce bekleyeceği süre.
    quota_cooldown_seconds: int = 3600
    # Modele konuşma geçmişi olarak verilen son tur sayısı (takip soruları için).
    history_turns: int = 6

    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # Google Cloud Console'dan alınan OAuth istemci kimliği; boşsa giriş uç noktası kapalıdır.
    google_client_id: str = ""
    jwt_secret: SecretStr = SecretStr("")
    jwt_ttl_hours: int = 720

    # Boşsa asistan konuşma geçmişi olmadan çalışır; sohbet etmek yine mümkündür.
    mongodb_uri: SecretStr | None = None
    mongodb_db: str = "atilim_assistant"

    # Model kotası API anahtarı başınadır, kullanıcı başına değil: tek kişi günlük kotayı
    # bitirip asistanı herkese kapatabilir. Bu sınır onu engeller.
    daily_question_limit: int = 30
    # Misafirin sınırı IP başınadır ve daha düşüktür: giriş gerektirmediği için kotayı
    # tüketmenin en kolay yolu misafirliktir.
    guest_daily_question_limit: int = 10
    # Vercel'in `/api` isteklerine eklediği `X-Proxy-Secret` başlığının değeri. Eşleşirse
    # misafirin adresi Vercel'in istemci IP başlıklarından alınır; boşsa bu başlıklara
    # güvenilmez ve Vercel üzerinden gelen misafirler Vercel'in çıkış adresini paylaşır.
    proxy_secret: SecretStr = SecretStr("")

    @property
    def vector_store_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def prepared_answers_path(self) -> Path:
        return self.data_dir / "prepared_answers.json"

    @property
    def catalog_path(self) -> Path:
        return self.data_dir / "catalog.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
