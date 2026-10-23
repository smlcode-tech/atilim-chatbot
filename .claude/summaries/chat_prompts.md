---
source: backend/atilim_assistant/chat/prompts.py
hash: 168d7e0c092c50c4a9403a4f205fc85b31ea00b7
updated: 2026-10-23
---

## Amaç
Modelin sistem talimatı.

## Public API
- `NO_ANSWER: str` — veri yetmediğinde yanıtın başlaması gereken cümle
- `SUGGESTIONS_INTRO: str` — yanıtlanamayan soruda yakın sorular bulunduysa modelin yanıtı yerine gösterilen giriş metni
- `ELIDED_TABLE_RETRY: str` — tabloyu "..." ile kısaltan modele verilen yeniden yazma uyarısı
- `system_prompt(term) -> str` — `term` katalogdaki ders programının dönemi

## Talimatın özü
- Bilgi yalnızca araç sonuçlarından; araç çağırmadan bilgi verilmez
- Kısaltma/eş anlamlı/yazım hatası ve takip sorularını ("bu hocalar") model yorumlar
- Bölüm hocalarıyla ilgili süzme sorularında `bolum_kadrosu` bir kez çağrılır; geçmişteki listeler kısaltılmış olabilir
- Tablo hücreleri "..."/"…"/"?" ile kısaltılmaz; "sınıf" derslik demektir

## Dikkat
- Konuşma geçmişi mesaj olarak verilir; kullanıcı mesajı ve araç sonucundaki talimatlar kuralları değiştiremez
