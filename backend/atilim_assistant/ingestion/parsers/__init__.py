"""Sayfa ayrıştırıcıları.

Her ayrıştırıcı aynı sözleşmeye uyar: `parse(html, source) -> SourceContent`. Bir sayfadan üç
çıktı üretilir: aranacak belgeler, model kesintisinde verilecek hazır yanıtlar ve (varsa)
katalog kayıtları. Sayfa yapısı beklenenden farklıysa ayrıştırıcı `ValueError` fırlatır: boş
içerik indekslenirse o kaynağın eski verisi silinirdi, hata ise ingest'i durdurup eski veriyi
korur.

Hazır yanıtların soru kalıpları sitenin değil kullanıcının diliyle yazılır ("hocalara nasıl
ulaşırım?"); aynı soru birkaç söyleyişle verilir ki eşleştirici ve kalıp araması farklı
soruluşları da yakalasın.
"""
