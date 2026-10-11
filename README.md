# Atılım Akademik Asistan

Atılım Üniversitesi web sitesini kaynak alan, Türkçe soru-cevap yapan RAG (Retrieval-Augmented
Generation) asistanı. Amaç, mevcut ve aday öğrencilerin sorularını hızlıca yanıtlayarak öğrenci
işlerinin yükünü azaltmaktır.

**Mevcut kapsam:** Yazılım Mühendisliği Bölümü akademik personeli. Kapsam, kaynak kataloğuna yeni
sayfalar eklenerek [atilim.edu.tr](https://www.atilim.edu.tr/tr) genelini kapsayacak şekilde
büyütülür (bkz. [Kapsamı genişletmek](#kapsamı-genişletmek)).

## Mimari

İki bağımsız akış vardır; ikisi yalnızca belge deposu üzerinden konuşur.

```
İndeksleme (çevrimdışı, CLI)
  kaynak kataloğu ──> sayfayı çek ──> ayrıştırıcı ──> Document[] ──> embedding ──> belge deposu
  ingestion/sources   ingestion/pipeline  ingestion/parsers            providers      retrieval/store

Soru-cevap (çevrimiçi, HTTP)
  React arayüzü ──> /api/chat ──> ChatService ──> HybridRetriever ──> belge deposu
                    api/          chat/           (vektör + BM25)
                                     └──> ChatModel (Gemini) ──> yanıt + kaynak bağlantıları
```

```
backend/
  atilim_assistant/
    config.py          Ortam değişkenleri / .env ayarları
    domain.py          Çekirdek tipler: Document, Source, Answer, Citation
    text.py            Türkçe metin normalleştirme
    ports.py           Model sağlayıcı arayüzleri: Embedder, ChatModel
    providers/         Arayüzlerin somut uygulamaları (Gemini)
    ingestion/         Kaynak kataloğu, sayfa ayrıştırıcıları, indeksleme adımları
    retrieval/         Belge deposu (Chroma), BM25 indeksi, hibrit getirici
    chat/              Sistem talimatı ve soru-cevap servisi
    api/               FastAPI uygulaması ve istek/yanıt şemaları
    bootstrap.py       Ayarlardan bileşenleri kuran bağlama noktası
    cli.py             Komut satırı: ingest, serve, chat
  tests/               Birim ve API testleri (ağ ve API anahtarı gerektirmez)
frontend/
  src/
    config/            Asistanın arayüzdeki adı, kapsam metinleri, öneri soruları
    api/               Backend istemcisi
    hooks/             Sohbet durumu (useChat)
    components/        Sidebar, Topbar, Welcome, MessageList, Composer
```

Temel tasarım kararları:

- **Tek belge modeli.** Her ayrıştırıcı sayfasını `Document` listesine çevirir; depo, getirici ve
  sohbet katmanı sayfanın türünü bilmez. Yeni içerik türü eklemek bu katmanlara dokunmaz.
- **Kaynak bazında indeksleme.** Bir kaynak yeniden indekslendiğinde yalnızca onun belgeleri
  değiştirilir; diğer kaynaklar etkilenmez.
- **Hibrit arama.** Anlamsal (vektör) arama ile anahtar kelime (BM25) araması Reciprocal Rank
  Fusion ile birleştirilir; böylece hem "makine öğrenmesi çalışanlar" hem de "Ali Yazıcı" gibi
  özel ad içeren sorular doğru belgeye ulaşır.
- **Değiştirilebilir model sağlayıcı.** Servisler `ports.py` arayüzlerine bağlıdır; başka bir
  sağlayıcıya geçmek için `providers/` altına yeni bir uygulama yazıp `bootstrap.py`'de bağlamak yeter.
- **Kaynak gösterimi.** Her yanıt, dayandığı sayfaların bağlantılarıyla birlikte döner.

## Kurulum

Gereksinimler: [uv](https://docs.astral.sh/uv/), Python 3.12 veya 3.13, Node.js 20+.

```bash
cd backend
uv sync                       # .venv oluşturur ve bağımlılıkları kurar
cp .env.example .env          # ardından GEMINI_API_KEY değerini yaz

cd ../frontend
npm install
```

## Çalıştırma

Backend komutları `backend/` klasöründen çalıştırılır:

```bash
uv run python -m atilim_assistant ingest    # kaynakları çek ve indeksle (backend/data/ altına yazar)
uv run python -m atilim_assistant serve     # API: http://127.0.0.1:8000
uv run python -m atilim_assistant chat      # terminalde sohbet (API gerekmez)
```

Arayüz için ikinci bir terminalde:

```bash
cd frontend
npm run dev
```

Vite'ın gösterdiği adresi tarayıcıda aç. Geliştirme sunucusu `/api` isteklerini
`127.0.0.1:8000` adresindeki API'ye yönlendirir. Üretim derlemesi `npm run build` ile
`frontend/dist/` klasörüne yazılır.

İndeks yeniden oluşturulduğunda değişikliklerin görünmesi için API yeniden başlatılmalıdır.

## API

| Uç nokta | İstek | Yanıt |
| --- | --- | --- |
| `GET /api/health` | — | `{"status": "ok"}` |
| `POST /api/chat` | `{"question": "..."}` (1-1000 karakter) | `{"answer": "...", "sources": [{"title": "...", "url": "..."}]}` |

Hatalar `{"detail": "..."}` gövdesiyle döner: geçersiz soru için 422, yanıt üretilemediğinde 502.

## Kapsamı genişletmek

1. `backend/atilim_assistant/ingestion/sources.py` içindeki `SOURCES` listesine yeni bir `Source` ekle.
2. Sayfa, mevcut ayrıştırıcılardan birinin beklediği yapıdaysa (ör. başka bir bölümün akademik
   personel sayfası) o ayrıştırıcıyı kullan. Değilse `ingestion/parsers/` altına
   `parse(html, source) -> list[Document]` imzalı yeni bir ayrıştırıcı ve `tests/` altına testini yaz.
3. Üretilen belgeleri indekslemeden incele, sonra indeksle:

   ```bash
   uv run python -m atilim_assistant ingest --source <kaynak-id> --dry-run
   uv run python -m atilim_assistant ingest --source <kaynak-id>
   ```

4. Arayüzdeki kapsam metinlerini ve öneri sorularını `frontend/src/config/assistant.ts` içinde güncelle.

## Test

```bash
cd backend && uv run pytest
cd frontend && npm run build      # tip denetimi + derleme
```

## Ayarlar

`backend/.env` dosyasından ya da ortam değişkenlerinden okunur.

| Değişken | Varsayılan | Açıklama |
| --- | --- | --- |
| `GEMINI_API_KEY` | — (zorunlu) | Google Gemini API anahtarı |
| `LLM_MODEL` | `gemini-3.8-flash` | Yanıt üreten model |
| `EMBED_MODEL` | `gemini-embedding-001` | Embedding modeli |
| `RETRIEVAL_TOP_K` | `6` | Modele bağlam olarak verilen belge sayısı |
| `DATA_DIR` | `backend/data` | İndeksin yazıldığı klasör |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | API'nin dinlediği adres |

`EMBED_MODEL` değiştirilirse indeks `ingest` ile yeniden oluşturulmalıdır.

## Sorun giderme

- **"İndeks boş" hatası:** önce `ingest` komutunu çalıştır.
- **"akademik personel kartı bulunamadı":** sitenin sayfa yapısı değişmiş olabilir. Sayfayı kaydedip
  `ingest --source <kaynak-id> --html sayfa.html --dry-run` ile ayrıştırıcıyı dene.
- **429 / RESOURCE_EXHAUSTED:** Gemini kotası doldu (ücretsiz katmanda model başına günlük istek
  sınırı vardır). Bekle ya da `LLM_MODEL` ile başka bir model seç.
- **Arayüzde "Sunucuya ulaşılamıyor":** API'nin `serve` komutuyla çalıştığını kontrol et.
