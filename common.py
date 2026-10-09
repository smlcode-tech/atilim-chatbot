import os
import re
import time

from google import genai
from google.genai import types

EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
DIM = 768  # Chroma cosine kullandığı için ayrıca normalize etmeye gerek yok

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

TR = str.maketrans("İIıŞşĞğÜüÖöÇç", "iiissgguuoocc")


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", s.translate(TR).lower())


def _retry(fn, tries=5):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            kota = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)
            if i == tries - 1 or not kota:
                raise
            time.sleep(5 * 2**i)


def embed(texts: list[str], task: str) -> list[list[float]]:
    """task: RETRIEVAL_DOCUMENT (indeksleme) veya RETRIEVAL_QUERY (soru)."""
    res = _retry(
        lambda: client.models.embed_content(
            model=EMBED_MODEL,
            contents=texts,
            config=types.EmbedContentConfig(task_type=task, output_dimensionality=DIM),
        )
    )
    return [e.values for e in res.embeddings]
