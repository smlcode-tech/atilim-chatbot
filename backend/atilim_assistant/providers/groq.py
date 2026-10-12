"""ChatModel arayüzünün Groq uygulaması (OpenAI uyumlu API)."""

from openai import OpenAI


class GroqProvider:
    def __init__(self, api_key: str, llm_model: str) -> None:
        self._client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        self._llm_model = llm_model

    def generate(self, system: str, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._llm_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        return response.choices[0].message.content or ""
