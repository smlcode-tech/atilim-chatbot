# Atılım YM Akademik Personel Chatbot (RAG)

Atılım Üniversitesi Yazılım Mühendisliği akademik personel sayfasını kaynak alan, Türkçe soru-cevap yapan RAG chatbot.

Akış: scrape.py -> people.json -> index.py (Gemini embedding + Chroma) -> chat.py (arama + Gemini cevap)

## Kurulum (Intel Mac için Python 3.13 gerekir; 3.14'te chromadb/onnxruntime kurulmaz)

    python3 -m pip install --user uv
    python3 -m uv venv --python 3.13 .venv
    source .venv/bin/activate
    python3 -m uv pip install -r requirements.txt

## API anahtarı (ekranda görünmeden gir, koda/GitHub'a yazma)

    read -s GEMINI_API_KEY && export GEMINI_API_KEY

İsteğe bağlı model ayarı: EMBED_MODEL (varsayılan gemini-embedding-001), LLM_MODEL (varsayılan gemini-2.5-flash).

## Chatbot web arayüzü

Önce akademik personel verisini ve vektör indeksini oluştur:

    python scrape.py    # sayfayı çeker, people.json üretir; çıktıdaki kişi sayısını kontrol et
    python index.py     # embedding üretir, chroma_db/ klasörüne yazar

Web arayüzü için iki terminal aç. İlk terminalde proje kökünden API'yi başlat:

    python server.py

İkinci terminalde React + TypeScript arayüzünü başlat:

    cd frontend
    npm install
    npm run dev

Vite'ın gösterdiği yerel adresi tarayıcıda aç. Geliştirme sunucusu `/api` isteklerini Python API'sine yönlendirir. API `127.0.0.1:8000` adresinde, web arayüzü ise Vite'ın seçtiği adreste çalışır. Gemini anahtarı, akademik personel verisi ve indeksleme adımları yukarıdaki gibi önceden hazırlanmış olmalıdır.

Üretim derlemesi için `cd frontend && npm run build` komutunu kullan. Derleme çıktısı `frontend/dist/` klasörüne yazılır; API için `python server.py` ayrıca çalışmaya devam etmelidir. `chat.py` terminalden doğrudan sohbet etmek için kullanılmaya devam eder.

Örnek sorular:
- Ali Yazıcı'nın araştırma konuları neler?
- Makine öğrenmesi çalışanlar kimler?

## Sorun giderme
- scrape.py 0 kişi bulursa: sayfanın HTML'ini kaydedip `python scrape.py sayfa.html` ile test et, h4 seçicisini düzelt.
- task_type hatası: common.py içinde EmbedContentConfig'den task_type'ı hem indekste hem sorguda kaldır.
- 429 / RESOURCE_EXHAUSTED: ücretsiz kota doldu; bekle ya da başka model seç.
