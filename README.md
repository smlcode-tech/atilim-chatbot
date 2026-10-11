# Atılım Akademik Asistan

Atılım Üniversitesi web sitesini kaynak alan, Türkçe soru-cevap yapan RAG (Retrieval-Augmented
Generation) asistanı. Amaç, mevcut ve aday öğrencilerin sorularını hızlıca yanıtlayarak öğrenci
işlerinin yükünü azaltmaktır.

**Mevcut kapsam:** Yazılım Mühendisliği Bölümü akademik personeli. Kapsam, kaynak kataloğuna yeni
sayfalar eklenerek [atilim.edu.tr](https://www.atilim.edu.tr/tr) genelini kapsayacak şekilde
büyütülür (bkz. [Kapsamı genişletmek](#kapsamı-genişletmek)).

## Mimari

İki bağımsız akış vardır; ikisi yalnızca `backend/data/` altındaki depolar üzerinden konuşur.

```
İndeksleme (çevrimdışı, CLI)
  kaynak kataloğu ──> sayfayı çek ──> ayrıştırıcı ─┬─> Document[] ──> embedding ──> belge deposu
  ingestion/sources   ingestion/pipeline  ingestion/parsers             providers      retrieval/store
                                                   └─> PreparedAnswer[] ──────────> hazır yanıt deposu
                                                                                    retrieval/prepared

Soru-cevap (çevrimiçi, HTTP)
  React arayüzü ──> /api/chat ──> ChatService ──> HybridRetriever ──> belge deposu
                    api/          chat/           (vektör + BM25)
                                     ├──> ChatModel (Gemini) ──> yanıt + kaynak bağlantıları
                                     └──> model yanıt üretemezse: PreparedAnswerMatcher ──> hazır yanıt
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
    retrieval/         Belge deposu (Chroma), BM25 indeksi, hibrit getirici, hazır yanıtlar
    chat/              Sistem talimatı ve soru-cevap servisi
    api/               FastAPI uygulaması ve istek/yanıt şemaları
    bootstrap.py       Ayarlardan bileşenleri kuran bağlama noktası
    cli.py             Komut satırı: ingest, serve, chat
  tests/               Birim ve API testleri (ağ ve API anahtarı gerektirmez)
frontend/
  vercel.json          Yayındaki arayüzün /api isteklerini API'ye yönlendirir
  src/
    config/            Asistanın arayüzdeki adı, kapsam metinleri, öneri soruları
    api/               Backend istemcisi
    hooks/             Sohbet durumu (useChat)
    components/        Sidebar, Topbar, Welcome, MessageList, Composer
render.yaml            API'nin Render'daki yayın tanımı
```

Temel tasarım kararları:

- **Tek belge modeli.** Her ayrıştırıcı sayfasını `Document` listesine çevirir; depo, getirici ve
  sohbet katmanı sayfanın türünü bilmez. Yeni içerik türü eklemek bu katmanlara dokunmaz.
- **Kaynak bazında indeksleme.** Bir kaynak yeniden indekslendiğinde yalnızca onun belgeleri ve
  hazır yanıtları değiştirilir; diğer kaynaklar etkilenmez.
- **Model kesintisine karşı hazır yanıtlar.** Ayrıştırıcılar, sayfa hakkında en sık sorulan
  sorular için soru-yanıt şablonlarını sayfanın verisiyle doldurur (ör. her akademisyenin
  tanıtımı, araştırma konuları, iletişimi; kadro listesi; konuya göre çalışanlar). Model yanıt
  üretemediğinde (kota, ağ, zaman aşımı) soru bu yanıtlarla, dış servise ihtiyaç duymayan yerel
  sözcük eşleştirmesiyle karşılanır. Şablonlar kodda, veri indekste durduğu için hazır yanıtlar
  her `ingest` ile sayfayla birlikte güncellenir. Yanıt, API'de ve arayüzde hazır yanıt olarak
  işaretlenir.
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
uv run python -m atilim_assistant ingest    # kaynakları çek, indeksle, hazır yanıtları üret (backend/data/)
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
| `POST /api/chat` | `{"question": "..."}` (1-1000 karakter) | `{"answer": "...", "sources": [{"title": "...", "url": "..."}], "prepared": false}` |

`prepared: true`, yanıtın model tarafından üretilmediğini, hazır yanıtlardan verildiğini belirtir.

Hatalar `{"detail": "..."}` gövdesiyle döner: geçersiz soru için 422; model yanıt üretemediğinde
ve soruyu karşılayan hazır yanıt da olmadığında 502.

## Kapsamı genişletmek

1. `backend/atilim_assistant/ingestion/sources.py` içindeki `SOURCES` listesine yeni bir `Source` ekle.
2. Sayfa, mevcut ayrıştırıcılardan birinin beklediği yapıdaysa (ör. başka bir bölümün akademik
   personel sayfası) o ayrıştırıcıyı kullan. Değilse `ingestion/parsers/` altına
   `parse(html, source) -> SourceContent` imzalı yeni bir ayrıştırıcı ve `tests/` altına testini yaz.
   Ayrıştırıcı, belgelerin yanında o sayfa için hazır yanıt şablonlarını da üretir; her hazır
   yanıtın `questions` listesi, kullanıcıların o bilgiyi sorarken kullanacağı sözcükleri içermelidir.
3. Üretilen belgeleri ve hazır yanıtları indekslemeden incele, sonra indeksle:

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

## Dağıtım

Proje, ücretsiz katmanlarla iki parça hâlinde yayınlanır:

| Parça | Platform | Tanım |
| --- | --- | --- |
| Arayüz | Vercel | GitHub deposu, kök klasör `frontend/` |
| API | Render (web servisi) | `render.yaml` |

Arayüz `/api/*` isteklerini `frontend/vercel.json` içindeki yönlendirmeyle API'ye iletir; API'nin
adresi yalnızca bu dosyada durur. Render'ın ücretsiz katmanında disk kalıcı olmadığı için indeks,
derleme sırasında `ingest` ile üretilir ve yayın paketine girer.

### İlk kurulum

1. Render'da **New → Blueprint** ile bu depoyu seç; `render.yaml` okunur ve servis oluşturulur.
   Sorulduğunda `GEMINI_API_KEY` değerini gir.
2. Servisin adresi `frontend/vercel.json` içindekinden farklıysa dosyayı güncelle.
3. Vercel'de depoyu içe aktar; **Root Directory** olarak `frontend` seç.

### Güncelleme

- **Kod:** `git push origin main`. `frontend/` değişiklikleri Vercel'de, `backend/` değişiklikleri
  Render'da kendiliğinden yeniden yayınlanır.
- **İndeks:** kaynak sayfalar değiştiğinde Render'da **Manual Deploy → Deploy latest commit**;
  derleme `ingest` komutunu baştan çalıştırır.
- **Ayarlar:** [Ayarlar](#ayarlar) tablosundaki değişkenler (ör. `LLM_MODEL`) Render'da servisin
  **Environment** bölümünden verilir.

Ücretsiz Render servisi 15 dakika istek almazsa uyur; sonraki ilk istek servisi uyandırır ve
yaklaşık bir dakika sürer.

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
- **Yanıtın altında "Yapay zekâ modeli şu anda yanıt üretemiyor" notu:** model hata verdi ve
  hazır yanıt gösterildi. Neden, API günlüğündeki "Model yanıt üretemedi" satırında yazar.
  Kesintiden sonraki ilk soru, modelin yeniden denemeleri bitene kadar (birkaç saniye) bekler;
  ardından model 60 saniye boyunca denenmez ve hazır yanıtlar anında verilir.
- **429 / RESOURCE_EXHAUSTED:** Gemini kotası doldu (ücretsiz katmanda model başına günlük istek
  sınırı vardır). Bekle ya da `LLM_MODEL` ile başka bir model seç.
- **"Hazır yanıt bulunamadı" uyarısı (API açılışında):** indeks, hazır yanıtlar eklenmeden önce
  oluşturulmuş. `ingest` komutunu yeniden çalıştır.
- **Arayüzde "Sunucuya ulaşılamıyor":** API'nin `serve` komutuyla çalıştığını kontrol et. Yayında
  ise Render servisi uykudan uyanıyor olabilir; bir dakika sonra yeniden dene, sürerse Render'daki
  servis günlüğüne bak.
