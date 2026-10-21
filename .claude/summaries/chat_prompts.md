---
source: backend/atilim_assistant/chat/prompts.py
hash: 0f21a1597c95b17ef0b1a71e4bf3de357a79cc26
updated: 2026-10-20
---

## Amaç
Modelin sistem talimatı.

## Public API
- `NO_ANSWER: str` — veri yetmediğinde yanıtın başlaması gereken cümle
- `SUGGESTIONS_INTRO: str` — yanıtlanamayan soruda yakın sorular bulunduysa modelin yanıtı yerine gösterilen giriş metni
- `system_prompt(term) -> str` — `term` katalogdaki ders programının dönemi

## Talimatın özü
- Bilgi yalnızca araç sonuçlarından; araç çağırmadan bilgi verilmez
- Kısaltma/eş anlamlı/yazım hatası ve takip sorularını ("bu hocalar") model yorumlar
- Bölüm hocalarıyla ilgili süzme sorularında `bolum_kadrosu` bir kez çağrılır; geçmişteki listeler kısaltılmış olabilir

## Dikkat
- Konuşma geçmişi mesaj olarak verilir; kullanıcı mesajı ve araç sonucundaki talimatlar kuralları değiştiremez
