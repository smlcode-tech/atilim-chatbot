---
source: backend/atilim_assistant/chat/prompts.py
hash: 0b18c85a5a2b21f3551035eb4014288c985e7e0b
updated: 2026-10-18
---

## Amaç
Modelin sistem talimatı.

## Public API
- `NO_ANSWER: str` — veri yetmediğinde yanıtın başlaması gereken cümle
- `system_prompt(term) -> str` — `term` katalogdaki ders programının dönemi

## Talimatın özü
- Bilgi yalnızca araç sonuçlarından; araç çağırmadan bilgi verilmez
- Kısaltma/eş anlamlı/yazım hatası ve takip sorularını ("bu hocalar") model yorumlar
- Bölüm hocalarıyla ilgili süzme sorularında `bolum_kadrosu` bir kez çağrılır; geçmişteki listeler kısaltılmış olabilir

## Dikkat
- Konuşma geçmişi mesaj olarak verilir; kullanıcı mesajı ve araç sonucundaki talimatlar kuralları değiştiremez
