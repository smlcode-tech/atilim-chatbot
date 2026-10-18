"""ChatModel arayüzünün Groq uygulaması (OpenAI uyumlu API)."""

from openai import OpenAI

from atilim_assistant.domain import Completion, ToolCall


class GroqProvider:
    def __init__(self, api_key: str, llm_model: str) -> None:
        self._client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        self._llm_model = llm_model

    def complete(self, messages: list[dict], tools: list[dict]) -> Completion:
        response = self._client.chat.completions.create(
            model=self._llm_model,
            messages=messages,
            temperature=0,
            # gpt-oss modelleri yanıttan önce "düşünür" ve bu da token kotasından yer. Ücretsiz
            # katmanın dakikalık sınırı (8000 token) varsayılan düzeyde bir-iki soruya yetiyor;
            # düşünme uzayınca yanıt çıkış sınırında kesilip boş da dönebiliyor.
            reasoning_effort="low",
            **({"tools": tools, "tool_choice": "auto"} if tools else {}),
        )
        message = response.choices[0].message
        return Completion(
            content=message.content or "",
            tool_calls=[
                ToolCall(id=call.id, name=call.function.name, arguments=call.function.arguments)
                for call in message.tool_calls or []
            ],
        )
