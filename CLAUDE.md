# Atılım Akademik Asistan — Proje Haritası

Atılım Üniversitesi web sitesi için Türkçe RAG chatbot. Kullanıcılar Google ile giriş yapar, soru sorar; sistem ChromaDB'den belge getirir (Voyage embedding), Groq ile yanıt üretir.

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
│   ├── service.py      Ana soru-cevap akışı; model hata yönetimi ve cooldown
│   ├── prompts.py      SYSTEM_PROMPT ve build_prompt(); CONTEXTUALIZE_PROMPT
│   └── contextualize.py  rewrite() — takip sorusu bağlamlandırma
├── providers/
│   ├── voyage.py       Voyage AI embedder adaptörü
│   └── groq.py         Groq adaptörü (yalnızca LLM, OpenAI uyumlu)
├── retrieval/
│   ├── retriever.py    HybridRetriever — vektör + BM25 + soru kalıbı birleşik arama
│   ├── store.py        ChromaDB sarmalayıcı
│   ├── lexical.py      BM25 anahtar kelime araması
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
| Groq | LLM (`openai/gpt-oss-120b`) | Ücretsiz katman dakikada 8000 token; bağlam `RETRIEVAL_MAX_CHARS` ile sınırlı |
| ChromaDB | Vektör depo (disk: `backend/data/chroma/`) | İndeks boşsa başlamaz |
| MongoDB | Konuşma geçmişi + kullanıcı | Opsiyonel; yoksa (ya da GOOGLE_CLIENT_ID yoksa) sorular misafir olarak, geçmişsiz yanıtlanır |

## Önemli Desenler
- **Ports/Adapters**: `ports.py`'daki Protocol'ler → somut implementasyonlar `providers/`, `storage/`
- **Uygulama fabrikası**: `create_app()` — testler sahte bileşen enjekte eder
- **Graceful degradation**: MongoDB, model veya kota hatası asistanı durdurmaz
- **Cooldown mekanizması**: Model hata verince `_model_retry_at` saati ilerletilir; hazır yanıtlar kullanılır
- **Bağlamlandırma**: geçmişi olan her soru modelle yeniden yazılır; ilk soruda ve soğuma süresinde atlanır. Sözcük kurallarıyla takip sorusu sezmek eş anlamlı ifadeleri kaçırdığı için bırakıldı
- **Eş anlamlı sözlük**: `text.SYNONYMS` / `canonicalize()` — "mail"/"e-posta", "hoca"/"öğretim üyesi" gibi söylenişleri kanonik biçime indirir; hazır yanıt eşleştirme ve BM25 hem soruya hem kalıba/belgeye uygular. Parser'larda soru kalıbı yazarken farklı söylenişler eklenir, ama veride olmayan bilgiyi soran kalıp eklenmez
- **Ders–hoca eşlemesi**: sitede hoca alanı boş (`academician_id` hep 0); `software_engineering/ders_programi.py` güncel dönemi EduPage API'sinden (`atilim.edupage.org/timetable`, `regularttGetData`) çeker, ders koduyla derse, ad eşleştirmesiyle (`same_person`) personele bağlar. `dersler` ve `academic_staff` ingest sırasında kullanır; program alınamazsa hoca bilgisi olmadan devam edilir. Testlerde `conftest` ağı kapatır
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
| `.claude/summaries/chat_contextualize.md` | `backend/atilim_assistant/chat/contextualize.py` |
| `.claude/summaries/storage_mongo.md` | `backend/atilim_assistant/storage/mongo.py` |
| `.claude/summaries/domain.md` | `backend/atilim_assistant/domain.py` |
| `.claude/summaries/bootstrap.md` | `backend/atilim_assistant/bootstrap.py` |
| `.claude/summaries/frontend_app.md` | `frontend/src/App.tsx` |
| `.claude/summaries/frontend_client.md` | `frontend/src/api/client.ts` |
| `.claude/summaries/frontend_usechat.md` | `frontend/src/hooks/useChat.ts` |
