import pytest

from atilim_assistant.chat.contextualize import needs_context, rewrite
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


@pytest.mark.parametrize(
    "question",
    [
        "Araştırma konuları neler?",
        "peki ya telefonu?",
        "Onun e-posta adresi ne?",
        "bu bölümde kaç öğretim üyesi var?",
        "detay ver",
        "ofisi nerede?",
    ],
)
def test_questions_leaning_on_earlier_turns_are_rewritten(question, history):
    assert needs_context(question, history) is True


@pytest.mark.parametrize(
    "question",
    [
        "Ali Yazıcı kim?",
        "Yazılım Mühendisliği bölüm başkanı kim?",
        "Blok zinciri ile ilgilenen öğretim üyeleri kimler?",
        "Bilgisayar Mühendisliği bölümünde bu yıl kaç öğrenci mezun oldu?",
    ],
)
def test_self_contained_questions_do_not_spend_a_model_call(question, history):
    assert needs_context(question, history) is False


def test_the_first_question_of_a_conversation_is_never_rewritten():
    assert needs_context("Araştırma konuları neler?", []) is False


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
