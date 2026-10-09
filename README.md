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

## Çalıştırma

    python scrape.py    # sayfayı çeker, people.json üretir; çıktıdaki kişi sayısını kontrol et
    python index.py     # embedding üretir, chroma_db/ klasörüne yazar
    python chat.py      # sohbet

Örnek sorular:
- Ali Yazıcı'nın araştırma konuları neler?
- Makine öğrenmesi çalışanlar kimler?

## Sorun giderme
- scrape.py 0 kişi bulursa: sayfanın HTML'ini kaydedip `python scrape.py sayfa.html` ile test et, h4 seçicisini düzelt.
- task_type hatası: common.py içinde EmbedContentConfig'den task_type'ı hem indekste hem sorguda kaldır.
- 429 / RESOURCE_EXHAUSTED: ücretsiz kota doldu; bekle ya da başka model seç.
