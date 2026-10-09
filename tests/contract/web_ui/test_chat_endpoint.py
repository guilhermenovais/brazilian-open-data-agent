"""Contract test for `POST /api/chat` (contracts/chat-api.md).

Drives the real Starlette app end-to-end via `starlette.testclient.TestClient`, with a
`FunctionModel`-backed `ConversationalAnswerer` double standing in for `QaAgentQuestionAnswerer`
(same model-override technique as
`tests/contract/qa_agent/test_answer_question_dispatch.py`) so no live model call is made.
"""

import json
from pathlib import Path

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from starlette.testclient import TestClient

from dataset_selector.briefing import FileBriefingSource
from dataset_selector.capabilities import select_dataset
from dataset_selector.exceptions import (
    BriefingNotFoundError,
    DatasetNotFoundError,
    NoBriefingsAvailableError,
)
from dataset_selector.locator import LocalDatasetLocator
from dataset_selector.selector import StaticDatasetSelector
from dataset_selector.usage_log import JsonlSelectionLogger
from qa_agent.capabilities import _answer_with_selection
from qa_agent.conversation import ConversationContext, ConversationTurn
from qa_agent.models import QuestionAnsweringResult
from qa_agent.run_log import JsonlRunLogger
from qa_agent.settings import AgentSettings
from web_ui.app import create_app

REPO_ROOT = Path(__file__).parent.parent.parent.parent
BRIEFINGS_ROOT = REPO_ROOT / "data" / "briefings"
DATASETS_ROOT = REPO_ROOT / "data" / "datasets"
QUESTION = "Quanto foi pago pela AEB em 2013?"
_NO_DATASET_ANSWER = "Não foi possível determinar a base de dados para responder a esta pergunta."
_UNKNOWN_DATASET_KEY = "<none>"


class _ScriptedQuestionAnswerer:
    """`QuestionAnswerer` + `ConversationalAnswerer` double answering via the real selection
    + agent-run path, with a scripted `FunctionModel` in place of a live model call — the
    same shape `QaAgentQuestionAnswerer` has, minus the fixed model resolution.
    `answer_turn` also records every `(message, context)` the endpoint passed in.
    """

    def __init__(self, model: FunctionModel, tmp_path: Path) -> None:
        self._model = model
        self._selector = StaticDatasetSelector(
            briefing_source=FileBriefingSource(BRIEFINGS_ROOT),
            locator=LocalDatasetLocator(DATASETS_ROOT),
        )
        self._selection_logger = JsonlSelectionLogger(tmp_path / "selections.jsonl")
        self._run_logger = JsonlRunLogger(tmp_path / "runs.jsonl")
        self._settings = AgentSettings(model_name="test", instrument=False)
        self.calls: list[str] = []
        self.turn_calls: list[tuple[str, ConversationContext]] = []

    def answer_turn(self, message: str, context: ConversationContext) -> QuestionAnsweringResult:
        self.turn_calls.append((message, context))
        return self.answer(message)

    def answer(self, question: str) -> QuestionAnsweringResult:
        self.calls.append(question)
        try:
            selection = select_dataset(question, selector=self._selector, logger=self._selection_logger)
        except (NoBriefingsAvailableError, DatasetNotFoundError, BriefingNotFoundError):
            return QuestionAnsweringResult(
                answer=_NO_DATASET_ANSWER,
                dataset_key=_UNKNOWN_DATASET_KEY,
                outcome="none",
                errored=True,
            )
        return _answer_with_selection(
            question,
            selection,
            run_logger=self._run_logger,
            settings=self._settings,
            model_override=self._model,
        )


def _scripted_answer(answer_text: str):
    def scripted(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(json.dumps({"answer": answer_text, "outcome": "full"}))])

    return scripted


def _submit_message_payload(text: str) -> dict:
    return {
        "id": "chat-1",
        "trigger": "submit-message",
        "messages": [
            {
                "id": "msg-1",
                "role": "user",
                "parts": [{"type": "text", "text": text}],
            }
        ],
    }


def _decode_sse_chunks(body: str) -> list[dict]:
    chunks = []
    for block in body.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        assert block.startswith("data: ")
        chunks.append(json.loads(block.removeprefix("data: ")))
    return chunks


def _text_from_chunks(chunks: list[dict]) -> str:
    return "".join(chunk["delta"] for chunk in chunks if chunk.get("type") == "text-delta")


def test_post_chat_returns_the_same_answer_the_answerer_returns_directly(tmp_path: Path) -> None:
    answerer = _ScriptedQuestionAnswerer(
        FunctionModel(_scripted_answer("O valor pago pela AEB em 2013 foi de R$ 42.")), tmp_path
    )
    direct_result = answerer.answer(QUESTION)
    # Reset the log-backed answerer's collaborators aren't stateful across calls in a way
    # that would change the second answer, so calling again through HTTP is safe to compare.
    app = create_app(answerer, host="127.0.0.1")
    client = TestClient(app, base_url="http://127.0.0.1")

    response = client.post("/api/chat", json=_submit_message_payload(QUESTION))

    assert response.status_code == 200
    chunks = _decode_sse_chunks(response.text)
    assert _text_from_chunks(chunks) == direct_result.answer
    assert chunks[-1]["type"] == "finish"
    assert chunks[-1]["finishReason"] == "stop"


def test_post_chat_with_empty_message_does_not_call_the_answerer(tmp_path: Path) -> None:
    answerer = _ScriptedQuestionAnswerer(FunctionModel(_scripted_answer("unused")), tmp_path)
    app = create_app(answerer, host="127.0.0.1")
    client = TestClient(app, base_url="http://127.0.0.1")

    response = client.post("/api/chat", json=_submit_message_payload("   "))

    assert response.status_code == 200
    chunks = _decode_sse_chunks(response.text)
    assert chunks == [{"type": "finish", "finishReason": "stop"}]
    assert answerer.calls == []


def test_post_chat_rejects_non_json_request_before_reaching_the_answerer(tmp_path: Path) -> None:
    answerer = _ScriptedQuestionAnswerer(FunctionModel(_scripted_answer("unused")), tmp_path)
    app = create_app(answerer, host="127.0.0.1")
    client = TestClient(app, base_url="http://127.0.0.1")

    response = client.post("/api/chat", content=b"not json", headers={"content-type": "text/plain"})

    assert response.status_code == 415
    assert answerer.calls == []


def test_options_chat_has_no_cors_headers(tmp_path: Path) -> None:
    answerer = _ScriptedQuestionAnswerer(FunctionModel(_scripted_answer("unused")), tmp_path)
    app = create_app(answerer, host="127.0.0.1")
    client = TestClient(app, base_url="http://127.0.0.1")

    response = client.options("/api/chat")

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


# --- 008: the conversation reaches answer_turn ---------------------------------------


def _conversation_payload(chat_id: str, texts: list[tuple[str, str]]) -> dict:
    return {
        "id": chat_id,
        "trigger": "submit-message",
        "messages": [
            {"id": f"m{i}", "role": role, "parts": [{"type": "text", "text": text}]}
            for i, (role, text) in enumerate(texts, start=1)
        ],
    }


def _client(answerer: _ScriptedQuestionAnswerer) -> TestClient:
    return TestClient(create_app(answerer, host="127.0.0.1"), base_url="http://127.0.0.1")


def test_the_contract_example_forwards_the_history_to_answer_turn(tmp_path: Path) -> None:
    answerer = _ScriptedQuestionAnswerer(FunctionModel(_scripted_answer("Em 2016, …")), tmp_path)

    response = _client(answerer).post(
        "/api/chat",
        json=_conversation_payload(
            "chat-1",
            [
                ("user", "Quanto foi pago pela AEB em 2015?"),
                ("assistant", "Em 2015, o valor pago foi de R$ …"),
                ("user", "e em 2016?"),
            ],
        ),
    )

    assert response.status_code == 200
    assert _text_from_chunks(_decode_sse_chunks(response.text)) == "Em 2016, …"
    assert answerer.turn_calls == [
        (
            "e em 2016?",
            ConversationContext(
                conversation_id="chat-1",
                turn_index=2,
                history=[
                    ConversationTurn(
                        question="Quanto foi pago pela AEB em 2015?",
                        answer="Em 2015, o valor pago foi de R$ …",
                    )
                ],
            ),
        )
    ]


def test_an_answerer_exception_still_becomes_the_generic_error_chunk(tmp_path: Path) -> None:
    class Exploding(_ScriptedQuestionAnswerer):
        def answer_turn(self, message, context):
            raise RuntimeError("secret sk-leak in a provider URL")

    answerer = Exploding(FunctionModel(_scripted_answer("unused")), tmp_path)

    response = _client(answerer).post("/api/chat", json=_submit_message_payload(QUESTION))

    chunks = _decode_sse_chunks(response.text)
    assert chunks == [{"type": "error", "errorText": "Ocorreu um erro inesperado ao processar a pergunta."}]


def test_interleaved_chats_only_see_their_own_messages(tmp_path: Path) -> None:
    """FR-007 / US3-AS2: no server-side state; each request's context is its own payload."""
    answerer = _ScriptedQuestionAnswerer(FunctionModel(_scripted_answer("ok")), tmp_path)
    client = _client(answerer)

    client.post("/api/chat", json=_conversation_payload("chat-a", [("user", "Quanto foi pago em 2015?")]))
    client.post("/api/chat", json=_conversation_payload("chat-b", [("user", "Quanto foi empenhado em 2012?")]))
    client.post(
        "/api/chat",
        json=_conversation_payload(
            "chat-a",
            [("user", "Quanto foi pago em 2015?"), ("assistant", "R$ 10"), ("user", "e em 2016?")],
        ),
    )
    client.post(
        "/api/chat",
        json=_conversation_payload(
            "chat-b",
            [("user", "Quanto foi empenhado em 2012?"), ("assistant", "R$ 20"), ("user", "e em 2013?")],
        ),
    )

    contexts = [context for _, context in answerer.turn_calls]
    assert [c.conversation_id for c in contexts] == ["chat-a", "chat-b", "chat-a", "chat-b"]
    assert contexts[2].history == [ConversationTurn(question="Quanto foi pago em 2015?", answer="R$ 10")]
    assert contexts[3].history == [ConversationTurn(question="Quanto foi empenhado em 2012?", answer="R$ 20")]


def test_a_new_chat_starts_empty_after_other_chats_on_the_same_app(tmp_path: Path) -> None:
    """FR-008 / US3-AS1."""
    answerer = _ScriptedQuestionAnswerer(FunctionModel(_scripted_answer("ok")), tmp_path)
    client = _client(answerer)
    client.post(
        "/api/chat",
        json=_conversation_payload(
            "chat-old",
            [("user", "Quanto foi pago em 2015?"), ("assistant", "R$ 10"), ("user", "e em 2016?")],
        ),
    )

    client.post("/api/chat", json=_conversation_payload("chat-new", [("user", "e em 2016?")]))

    message, context = answerer.turn_calls[-1]
    assert message == "e em 2016?"
    assert context.conversation_id == "chat-new"
    assert context.history == []
    assert context.turn_index == 1
