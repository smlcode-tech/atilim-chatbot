from atilim_assistant.providers.groq import GroqProvider
from atilim_assistant.providers.voyage import VoyageEmbedder


def test_model_requests_cannot_hang_for_the_clients_ten_minute_default():
    client = GroqProvider("test-key", "openai/gpt-oss-120b")._client
    assert client.timeout == 60
    assert client.max_retries == 2


def test_embedding_requests_time_out_and_are_retried():
    client = VoyageEmbedder("test-key", "voyage-multilingual-2")._client
    assert client._params["request_timeout"] == 20
    assert client.max_retries == 3
