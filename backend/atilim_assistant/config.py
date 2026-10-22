"""Ortam değişkenlerinden ve backend/.env dosyasından okunan uygulama ayarları.

Tüm ayarlar tek sınıfta toplanır; kod ortam değişkenlerini kendisi okumaz. Böylece her ayarın
varsayılanı ve açıklaması tek yerde durur, testler sahte bir `Settings` verebilir. Ortam
değişkeni adı alan adının büyük harflisidir (`groq_api_key` → `GROQ_API_KEY`).
"""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Göreli yollar çalışma dizinine göre değil bu konuma göre çözülür: komut nereden çalıştırılırsa
# çalıştırılsın aynı `data/` ve `.env` kullanılır.
BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Uygulamanın tüm ayarları; yalnızca API anahtarları zorunludur, geri kalanın varsayılanı vardır."""

    # Tanımlanmamış ortam değişkenleri yok sayılır: Render ve .env bu uygulamanın okumadığı
    # değişkenler de içerebilir (ör. `PYTHON_VERSION`).
    model_config = SettingsConfigDict(env_file=BACKEND_ROOT / ".env", extra="ignore")

    # Anahtarlar `SecretStr`'dir: kayıtlara ve hata mesajlarına yazdırıldığında gizlenir.
    groq_api_key: SecretStr
    voyage_api_key: SecretStr
    llm_model: str = "openai/gpt-oss-120b"
    # Değişirse indeks silinip yeniden kurulmalıdır (bkz. `DocumentStore`).
    embed_model: str = "voyage-multilingual-2"

    # İndeks, katalog ve hazır yanıtların dizini; ingest yazar, API okur.
    data_dir: Path = BACKEND_ROOT / "data"
    # Chroma koleksiyonunun adı; soru kalıpları `<collection>_questions` koleksiyonundadır.
    collection: str = "atilim_documents"
    # Her arama yönteminden alınan ve modele verilen belge sayısı.
    retrieval_top_k: int = 6

    # Kota bittiğinde modelin yeniden denenmeden önce bekleyeceği süre.
    quota_cooldown_seconds: int = 3600
    # Modele konuşma geçmişi olarak verilen son tur sayısı (takip soruları için).
    history_turns: int = 6

    # `cli serve`'ün dinlediği adres. Varsayılan yalnızca yerel makinedir; Render'da
    # `render.yaml` 0.0.0.0 ve platformun verdiği portu atar.
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # Google Cloud Console'dan alınan OAuth istemci kimliği; boşsa giriş uç noktası kapalıdır.
    google_client_id: str = ""
    # Oturum jetonlarının imza anahtarı; en az 32 bayt olmalıdır, yoksa giriş kapatılır.
    jwt_secret: SecretStr = SecretStr("")
    # Oturum süresi (30 gün); dolunca kullanıcı yeniden Google ile giriş yapar.
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

    # Dosya yolları ayar değil, `data_dir`'den türetilir: tek bir dizin değiştirilerek tüm
    # veri başka yere taşınabilir.
    @property
    def vector_store_dir(self) -> Path:
        """Chroma indeksinin dizini."""
        return self.data_dir / "chroma"

    @property
    def prepared_answers_path(self) -> Path:
        """Hazır yanıtların JSON dosyası."""
        return self.data_dir / "prepared_answers.json"

    @property
    def catalog_path(self) -> Path:
        """Yapılandırılmış katalogun JSON dosyası."""
        return self.data_dir / "catalog.json"


@lru_cache
def get_settings() -> Settings:
    """Ayarlar süreç başına bir kez okunur; `.env` her çağrıda yeniden ayrıştırılmaz."""
    return Settings()
