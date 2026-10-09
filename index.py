import json

import chromadb

from common import embed

COLLECTION = "akademik_personel"

people = json.load(open("people.json", encoding="utf-8"))
docs = [p["metin"] for p in people]

db = chromadb.PersistentClient(path="chroma_db")
try:
    db.delete_collection(COLLECTION)  # her çalıştırmada sıfırdan kur
except Exception:
    pass
col = db.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

col.add(
    ids=[str(i) for i in range(len(people))],
    documents=docs,
    embeddings=embed(docs, "RETRIEVAL_DOCUMENT"),
    metadatas=[
        {"ad": p["ad"], "unvan": p["unvan"], "gorev": p["gorev"] or "-"}
        for p in people
    ],
)
print(f"{col.count()} kayıt indekslendi")
