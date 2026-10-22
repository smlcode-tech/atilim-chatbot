# Atılım Akademik Asistan — Proje Haritası

Atılım Üniversitesi web sitesi için Türkçe chatbot. Kullanıcılar Google ile giriş yapar, soru sorar; Groq modeli araçlarla (tool calling) yapılandırılmış kataloğu ve ChromaDB belge aramasını (Voyage embedding) sorgulayıp yanıt üretir.

## Dağıtım
- **Backend**: Render.com (ücretsiz) → `render.yaml`
- **Frontend**: Vercel → `frontend/vercel.json`

## Dizin Yapısı

```
backend/atilim_assistant/
├── api/
│   ├── app.py          FastAPI uygulama fabrikası; tüm HTTP rotaları burada
│   └── schemas.py      Pydantic istek/yanıt modelleri
├── chat/
│   ├── service.py      Ana soru-cevap akışı: araç çağrılı model döngüsü, cooldown, hazır yanıt yedeği
│   ├── tools.py        Modelin araçları: ders_ara, ders_detayi, hocanin_dersleri, bolum_kadrosu, personel_bilgisi, belge_ara
│   └── prompts.py      system_prompt(term), NO_ANSWER
├── providers/
│   ├── voyage.py       Voyage AI embedder adaptörü
│   └── groq.py         Groq adaptörü (yalnızca LLM, OpenAI uyumlu)
├── retrieval/
│   ├── retriever.py    HybridRetriever — vektör + BM25 + soru kalıbı birleşik arama
│   ├── store.py        ChromaDB sarmalayıcı
│   ├── lexical.py      BM25 anahtar kelime araması
│   ├── catalog.py      CatalogStore — ders, kadro, ders programı kayıtları (data/catalog.json)
│   └── prepared.py     PreparedAnswerMatcher — model olmadan hazır yanıt
├── storage/
│   └── mongo.py        MongoUserRepository + MongoConversationRepository
├── ingestion/
│   ├── pipeline.py     Veri alım akışı
│   ├── sources.py      Web scraping / kaynak tanımları
│   └── parsers/        Sayfa bazlı ayrıştırıcılar
├── domain.py           Tüm veri sınıfları: Document, Turn, Answer, User, vb.
├── ports.py            Protocol arayüzleri: ChatModel, Embedder, Repo'lar
├── config.py           Pydantic Settings + lru_cache get_settings()
├── bootstrap.py        Bileşen bağlama: build_chat_service(), build_provider()
└── auth.py             JWT + Google OAuth JWKS doğrulaması

frontend/src/
├── App.tsx             Kök bileşen; splash, auth, drawer, Cmd+K kısayolu
├── api/client.ts       fetch sarmalayıcıları; token yönetimi; hata tipleri
├── hooks/
│   ├── useAuth.ts      Google giriş durumu
│   ├── useChat.ts      Mesaj durumu + API çağrıları
│   ├── useConversations.ts  Yan bar konuşma listesi
│   └── useTheme.ts     Açık/koyu tema
└── components/         UI bileşenleri (Composer, MessageList, Sidebar, vb.)
```

## Kritik Bağımlılıklar
| Servis | Amaç | Not |
|--------|------|-----|
| Voyage AI | Embedding (`voyage-multilingual-2`, 1024 boyut) | Model değişirse indeks silinip yeniden kurulmalı; `DocumentStore` uyuşmazlıkta açılmaz |
| Groq | LLM (`openai/gpt-oss-120b`, tool calling, `reasoning_effort="low"`) | Ücretsiz katman dakikada 8000 token; soru başına 2–5 model çağrısı, ~2–8 bin token. Sınır aşılınca OpenAI istemcisi bekleyip yeniden dener (yanıt 30–60 sn sürebilir) |
| EduPage | Ders programı (`atilim.edupage.org/timetable`) | Ingest'te çekilir, katalogda tutulur; yalnızca güncel dönem |
| ChromaDB | Vektör depo (disk: `backend/data/chroma/`) | İndeks boşsa başlamaz |
| MongoDB | Konuşma geçmişi + kullanıcı + soru sayaçları | Opsiyonel; yoksa (ya da GOOGLE_CLIENT_ID yoksa) herkes misafirdir ve günlük sınır uygulanamaz |

## Önemli Desenler
- **Ports/Adapters**: `ports.py`'daki Protocol'ler → somut implementasyonlar `providers/`, `storage/`
- **Uygulama fabrikası**: `create_app()` — testler sahte bileşen enjekte eder
- **Misafir girişi**: giriş açıkken de jetonsuz istek misafirdir (`auth.chat_user`); geçersiz jeton ise 401 (süresi dolan oturum sessizce misafire düşmez). Misafirin geçmişi sunucuda tutulmaz, takip soruları için tarayıcı `ChatRequest.history` gönderir (girişli kullanıcıda yok sayılır). Misafir sınırı IP başına günlük `guest_daily_question_limit` (10; girişli kullanıcıda `daily_question_limit`). Kalan hak `GET /api/quota` ve her `ChatResponse.remaining` ile arayüze gider (sayacı değiştirmeden okur, yanıtlanamayan soru geri düşülür); sayaç `guest_quotas` koleksiyonunda, IP'nin SHA-256 özetiyle; IP `api.app._client_ip`: Vercel `/api` isteklerine `X-Proxy-Secret` ekler (`frontend/vercel.json` transform'u, Vercel ve Render'da aynı `PROXY_SECRET`); eşleşirse adres Vercel'in `X-Vercel-Forwarded-For` / `X-Real-IP` başlığından, eşleşmezse `X-Forwarded-For`'un **son** öğesinden alınır (baştakileri istemci uydurabilir; Vercel üzerinden gelende son öğe Vercel'in çıkış adresidir)
- **Graceful degradation**: MongoDB, model veya kota hatası asistanı durdurmaz
- **Araç çağrılı model (tool calling)**: söyleyişi (kısaltma, eş anlamlı, takip sorusu) model yorumlar, veriyi araçlarla kesin alır; her söyleyiş için kural/kalıp yazılmaz. Liste/süzme soruları katalogun tamamı üzerinde hesaplanır. Model geçmişi mesaj olarak görür; ayrı bağlamlandırma (yeniden yazma) çağrısı kaldırıldı. Yeni yapılandırılmış veri → parser `records` döndürür, `chat/tools.py`'ye araç eklenir
- **Hazır yanıtlar yalnızca yedek**: model çalışırken her soru modele gider; model hata verince ya da soğumadayken hazır yanıt eşleştirilir. İstisna: soru bir kalıbın birebir aynısıysa (seçilen öneri) hazır yanıt hemen verilir
- **"Bilmiyorum" yerine seçenekler**: model `NO_ANSWER` döndürürse `HybridRetriever.similar_questions` en yakın 5 soru kalıbını önerir (her yanıttan ve her kalıp biçiminden biri; soruyla ortak içerik sözcüğü ya da ≥0.45 kosinüs benzerliği şart — ilgisiz soruya öneri çıkmaz). Arayüz bunları + "Diğer" seçeneğini son yanıtın altında gösterir; öneriler Mongo'da turla saklanır
- **Cooldown mekanizması**: Model hata verince `_model_retry_at` saati ilerletilir; hazır yanıtlar kullanılır
- **Ders kodu düzeltme**: `ChatService.answer` önce `tools.correct()` çağırır; indekste olmayan kod, sayısı aynı ve harfi tek düzenleme uzaktaki tek bilinen koda çevrilir ("MATF276" → "MATH276"). `stem()` rakamlı terimleri kısaltmaz
- **Eş anlamlı sözlük**: `text.SYNONYMS` / `canonicalize()` — hazır yanıt eşleştirme (yedek yol) ve BM25 (`belge_ara`) için; model yolunda yorumu model yapar. Veride olmayan bilgiyi soran soru kalıbı eklenmez
- **Ders–hoca eşlemesi**: sitede hoca alanı boş (`academician_id` hep 0); `software_engineering/ders_programi.py` güncel dönemi EduPage API'sinden (`atilim.edupage.org/timetable`, `regularttGetData`) çeker, ders koduyla derse, ad eşleştirmesiyle (`same_person`) personele bağlar. `dersler` ve `academic_staff` ingest sırasında kullanır, `cli ingest` tüm programı kataloğa yazar; program alınamazsa hoca bilgisi olmadan devam edilir. Testlerde `conftest` ağı kapatır
- **Soru kalıbı indeksi**: hazır yanıtların soru kalıpları `<collection>_questions` koleksiyonunda embedding'lenir; retrieval'a üçüncü sıralama olarak katılır ve yanıtı bağlam olarak modele verir (eşik yok, alaka kararını model verir)

## Geliştirme Komutları
```bash
# Backend
cd backend
uv run uvicorn atilim_assistant.api.app:create_app --factory --reload

# Frontend
cd frontend
npm run dev          # http://localhost:5173

# Test
cd backend
uv run pytest

# İndeks oluştur
cd backend
uv run python -m atilim_assistant ingest
```

## Dosya Özetleri
Her kritik dosyanın özetini `.claude/summaries/` altında bul.
Hash kontrolü: `git hash-object <dosya>` — özetteki hash ile eşleşiyorsa tam dosyayı okuma.

| Özet | Kaynak |
|------|--------|
| `.claude/summaries/api_app.md` | `backend/atilim_assistant/api/app.py` |
| `.claude/summaries/api_schemas.md` | `backend/atilim_assistant/api/schemas.py` |
| `.claude/summaries/chat_service.md` | `backend/atilim_assistant/chat/service.py` |
| `.claude/summaries/chat_prompts.md` | `backend/atilim_assistant/chat/prompts.py` |
| `.claude/summaries/storage_mongo.md` | `backend/atilim_assistant/storage/mongo.py` |
| `.claude/summaries/domain.md` | `backend/atilim_assistant/domain.py` |
| `.claude/summaries/bootstrap.md` | `backend/atilim_assistant/bootstrap.py` |
| `.claude/summaries/frontend_app.md` | `frontend/src/App.tsx` |
| `.claude/summaries/frontend_client.md` | `frontend/src/api/client.ts` |
| `.claude/summaries/frontend_usechat.md` | `frontend/src/hooks/useChat.ts` |
