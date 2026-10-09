import json

import chromadb
from google.genai import types

from common import LLM_MODEL, client, embed, norm

people = json.load(open("people.json", encoding="utf-8"))
col = chromadb.PersistentClient(path="chroma_db").get_collection("akademik_personel")

SYSTEM = (
    "Sen Atılım Üniversitesi Yazılım Mühendisliği bölümü akademik personel asistanısın. "
    "Yalnızca verilen BAĞLAM'daki bilgilere dayanarak Türkçe cevap ver. "
    "Bağlamda olmayan bilgiyi uydurma; yoksa 'Bu bilgi elimdeki verilerde yok' de. "
    "Araştırma konuları istenirse bağlamdaki listeyi eksiksiz, madde madde ver."
)


def retrieve(soru: str, k: int = 4) -> list[str]:
    # 1) anlamsal arama (Chroma)
    qv = embed([soru], "RETRIEVAL_QUERY")[0]
    vektor_sonuc = col.query(query_embeddings=[qv], n_results=k)["documents"][0]

    # 2) isim eşleşmesi (embedding özel isimde zayıf olduğu için)
    sorgu_tokenlari = set(norm(soru).split())
    isim_sonuc = []
    for p in people:
        ad_tokenlari = norm(p["ad"]).split()
        if len(set(ad_tokenlari) & sorgu_tokenlari) >= 2 or ad_tokenlari[-1] in sorgu_tokenlari:
            isim_sonuc.append(p["metin"])

    # isim eşleşenler öne, tekrarlar elenir
    sonuc = []
    for d in isim_sonuc + vektor_sonuc:
        if d not in sonuc:
            sonuc.append(d)
    return sonuc[: max(k, len(isim_sonuc))]


while True:
    soru = input("\nSoru (çıkış: q): ").strip()
    if soru.lower() == "q":
        break
    baglam = "\n\n---\n\n".join(retrieve(soru))
    stream = client.models.generate_content_stream(
        model=LLM_MODEL,
        contents=f"BAĞLAM:\n{baglam}\n\nSORU: {soru}",
        config=types.GenerateContentConfig(system_instruction=SYSTEM, temperature=0),
    )
    for parca in stream:
        print(parca.text or "", end="", flush=True)
    print()
