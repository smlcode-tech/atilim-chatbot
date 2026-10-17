import pytest

from atilim_assistant.chat.contextualize import rewrite
from atilim_assistant.domain import Turn


@pytest.fixture
def history() -> list[Turn]:
    return [
        Turn(role="user", content="Ali Yazıcı kim?"),
        Turn(role="assistant", content="Ali Yazıcı, Yazılım Mühendisliği bölümünde profesördür."),
    ]


class FakeModel:
    def __init__(self, reply: str = "Ali Yazıcı'nın araştırma konuları neler?"):
        self.reply = reply
        self.prompt = None

    def generate(self, system, prompt):
        self.prompt = prompt
        return self.reply


def test_rewrite_feeds_the_model_both_the_history_and_the_question(history):
    model = FakeModel()

    assert rewrite("Araştırma konuları neler?", history, model) == (
        "Ali Yazıcı'nın araştırma konuları neler?"
    )
    assert "Kullanıcı: Ali Yazıcı kim?" in model.prompt
    assert model.prompt.endswith("SON SORU: Araştırma konuları neler?")


@pytest.mark.parametrize("reply", ["", "   ", "Birinci satır\nİkinci satır", "uzun " * 60])
def test_unusable_rewrites_fall_back_to_the_original_question(reply, history):
    question = "Araştırma konuları neler?"

    assert rewrite(question, history, FakeModel(reply)) == question


def test_long_turns_are_clipped_before_rewriting(history):
    model = FakeModel()
    long_answer = Turn(role="assistant", content="Kadro: " + "Ad SOYAD, " * 200)

    rewrite("Bunlara nasıl ulaşırım?", [*history, long_answer], model)

    assert len(model.prompt) < 1000
