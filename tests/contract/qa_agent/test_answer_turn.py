"""Contract tests for qa_agent.answer_turn (008 contracts/conversational-answering.md).

These check the mechanism, not answer quality: what the model actually receives (history
as text-only prior messages, the v2 instructions), that every turn gets a fresh step
budget, that `steps` are current-turn only, and what the run log records. Answer quality
for follow-ups and clarifications is measured by the live `run-conversations` runner.

The real `answer_turn` and the real `_answer_with_selection` run end to end; the only
substitution is a scripted `FunctionModel`, injected by wrapping `_answer_with_selection`
with a `model_override` (the same test seam the other qa_agent contract tests use).
"""

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

import qa_agent.capabilities as qa_capabilities
from dataset_selector.briefing import FileBriefingSource
from dataset_selector.locator import LocalDatasetLocator
from dataset_selector.selector import StaticDatasetSelector
from dataset_selector.usage_log import JsonlSelectionLogger
from qa_agent.capabilities import _NO_DATASET_ANSWER, answer_turn
from qa_agent.conversation import ConversationContext, ConversationTurn
from qa_agent.deps import AgentDeps
from qa_agent.models import QuestionAnsweringResult
from qa_agent.prompt_loader import render
from qa_agent.run_log import JsonlRunLogger
from qa_agent.settings import AgentSettings
from qa_agent.step_budget import RETRIEVAL_STEP_LIMIT

REPO_ROOT = Path(__file__).parent.parent.parent.parent
BRIEFINGS_ROOT = REPO_ROOT / "data" / "briefings"
DATASETS_ROOT = REPO_ROOT / "data" / "datasets"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "qa_agent"
DATASET_KEY = "orcamentos-aeb-csv"

Scripted = Callable[[list[ModelMessage], AgentInfo], ModelResponse]


def _final(answer: str = "ok", outcome: str = "full") -> ModelResponse:
    return ModelResponse(parts=[TextPart(json.dumps({"answer": answer, "outcome": outcome}))])


def _answer_directly(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return _final()


class Harness:
    """Runs the real `answer_turn` against a scripted model, recording what it received."""

    def __init__(self, tmp_path: Path, monkeypatch, *, history_char_limit: int = 16_000,
                 briefings_root: Path = BRIEFINGS_ROOT, datasets_root: Path = DATASETS_ROOT) -> None:
        self.log_path = tmp_path / "runs.jsonl"
        self.received: list[tuple[list[ModelMessage], str | None]] = []
        self.deps: list[AgentDeps] = []
        self.script: Scripted = _answer_directly
        self._selector = StaticDatasetSelector(
            briefing_source=FileBriefingSource(briefings_root),
            locator=LocalDatasetLocator(datasets_root),
        )
        self._selection_logger = JsonlSelectionLogger(tmp_path / "selections.jsonl")
        self._settings = AgentSettings(
            model_name="test", instrument=False, history_char_limit=history_char_limit
        )

        def recording(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            self.received.append((list(messages), info.instructions))
            return self.script(messages, info)

        real = qa_capabilities._answer_with_selection
        model = FunctionModel(recording)

        def with_scripted_model(*args, **kwargs):
            return real(*args, model_override=model, capture_deps=self.deps, **kwargs)

        monkeypatch.setattr(qa_capabilities, "_answer_with_selection", with_scripted_model)

    def turn(self, message: str, history: list[ConversationTurn], conversation_id: str = "chat-1"):
        context = ConversationContext(
            conversation_id=conversation_id, turn_index=len(history) + 1, history=history
        )
        return answer_turn(
            message,
            context=context,
            selector=self._selector,
            selection_logger=self._selection_logger,
            run_logger=JsonlRunLogger(self.log_path),
            settings=self._settings,
        )

    def log_lines(self) -> list[dict]:
        return [json.loads(line) for line in self.log_path.read_text().splitlines()]


HISTORY = [
    ConversationTurn(question="Quanto foi pago pela AEB em 2015?", answer="Em 2015 foram pagos R$ 10."),
    ConversationTurn(question="Pergunta que falhou", answer=None),
    ConversationTurn(question="E o empenhado?", answer="Foram empenhados R$ 12."),
]


def test_history_reaches_the_model_as_text_only_prior_messages(tmp_path: Path, monkeypatch) -> None:
    harness = Harness(tmp_path, monkeypatch)

    harness.turn("e em 2016?", HISTORY)

    messages, _ = harness.received[0]
    *prior, current = messages
    # The unanswered turn (answer=None) is built as a request with no response after it;
    # pydantic-ai merges it with the next turn's request, so that request holds two user parts.
    assert [type(m) for m in prior] == [ModelRequest, ModelResponse, ModelRequest, ModelResponse]
    texts = [
        part.content
        for m in prior
        for part in m.parts
        if isinstance(part, (UserPromptPart, TextPart))
    ]
    assert texts == [
        "Quanto foi pago pela AEB em 2015?",
        "Em 2015 foram pagos R$ 10.",
        "Pergunta que falhou",
        "E o empenhado?",
        "Foram empenhados R$ 12.",
    ]
    assert all(
        isinstance(part, (UserPromptPart, TextPart)) for m in prior for part in m.parts
    ), "FR-001: no tool call or return from an earlier turn may reach the model"
    assert isinstance(current, ModelRequest)
    assert [p.content for p in current.parts if isinstance(p, UserPromptPart)] == ["e em 2016?"]


def test_instructions_are_rendered_from_system_v2(tmp_path: Path, monkeypatch) -> None:
    harness = Harness(tmp_path, monkeypatch)

    harness.turn("Quanto foi pago pela AEB em 2016?", [])

    _, instructions = harness.received[0]
    briefing = (BRIEFINGS_ROOT / f"{DATASET_KEY}.md").read_text()
    assert instructions == render(briefing, version="v2").strip()


def _use_every_step_then_answer(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    calls_so_far = sum(
        1 for m in messages if isinstance(m, ModelResponse) for p in m.parts if isinstance(p, ToolCallPart)
    )
    if calls_so_far < RETRIEVAL_STEP_LIMIT:
        return ModelResponse(parts=[ToolCallPart(tool_name="discover_data_sources", args={})])
    return _final()


def test_each_turn_gets_a_fresh_step_budget(tmp_path: Path, monkeypatch) -> None:
    """FR-009: a turn after one that used all 10 retrieval steps still has all 10."""
    harness = Harness(tmp_path, monkeypatch)
    harness.script = _use_every_step_then_answer

    first = harness.turn("Quanto foi pago pela AEB em 2015?", [])
    harness.turn("e em 2016?", [ConversationTurn(question="Quanto foi pago pela AEB em 2015?", answer=first.answer)])

    first_budget, second_budget = harness.deps[0].step_budget, harness.deps[1].step_budget
    assert first_budget is not second_budget
    assert first_budget.attempts == RETRIEVAL_STEP_LIMIT
    assert second_budget.limit == RETRIEVAL_STEP_LIMIT
    assert second_budget.attempts == RETRIEVAL_STEP_LIMIT


def _one_tool_call_then_answer(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    if not any(isinstance(p, ToolReturnPart) for m in messages for p in m.parts):
        return ModelResponse(parts=[ToolCallPart(tool_name="discover_data_sources", args={})])
    return _final()


def test_steps_hold_only_the_current_turns_retrievals(tmp_path: Path, monkeypatch) -> None:
    harness = Harness(tmp_path, monkeypatch)
    harness.script = _one_tool_call_then_answer

    result = harness.turn("e em 2016?", HISTORY)

    assert [s.tool_name for s in result.steps] == ["discover_data_sources"]


def test_one_log_line_with_the_conversation_block(tmp_path: Path, monkeypatch) -> None:
    harness = Harness(tmp_path, monkeypatch)

    harness.turn("e em 2016?", HISTORY, conversation_id="chat-42")

    (line,) = harness.log_lines()
    assert line["question"] == "e em 2016?"
    assert line["conversation"] == {
        "conversation_id": "chat-42",
        "turn_index": 4,
        "history_turns_used": 3,
        "history_turns_dropped": 0,
        "history_char_limit": 16_000,
        "prompt_version": "v2",
    }


def test_a_small_limit_drops_the_oldest_turns_and_still_answers(tmp_path: Path, monkeypatch) -> None:
    """FR-011: only the most recent turn fits; the turn is answered anyway."""
    newest = HISTORY[-1]
    harness = Harness(tmp_path, monkeypatch, history_char_limit=newest.size)

    result = harness.turn("e em 2016?", HISTORY)

    assert not result.errored
    messages, _ = harness.received[0]
    prior_texts = [
        p.content for m in messages[:-1] for p in m.parts if isinstance(p, (UserPromptPart, TextPart))
    ]
    assert prior_texts == [newest.question, newest.answer]
    conversation = harness.log_lines()[0]["conversation"]
    assert conversation["history_turns_used"] == 1
    assert conversation["history_turns_dropped"] == 2


def test_answer_turn_delegates_after_a_real_selection(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, object] = {}
    sentinel = QuestionAnsweringResult(answer="x", dataset_key=DATASET_KEY, outcome="full")

    def fake(question, selection, *, run_logger, settings, **kwargs):
        captured.update(question=question, selection=selection, **kwargs)
        return sentinel

    monkeypatch.setattr(qa_capabilities, "_answer_with_selection", fake)
    context = ConversationContext(conversation_id="c", turn_index=2, history=HISTORY[:1])

    result = answer_turn(
        "e em 2016?",
        context=context,
        selector=StaticDatasetSelector(
            briefing_source=FileBriefingSource(BRIEFINGS_ROOT),
            locator=LocalDatasetLocator(DATASETS_ROOT),
        ),
        selection_logger=JsonlSelectionLogger(tmp_path / "selections.jsonl"),
        run_logger=JsonlRunLogger(tmp_path / "runs.jsonl"),
        settings=AgentSettings(model_name="test", instrument=False),
    )

    assert result is sentinel
    assert captured["question"] == "e em 2016?"
    assert captured["selection"].dataset_key == DATASET_KEY  # type: ignore[attr-defined]
    assert captured["history"] == HISTORY[:1]
    assert captured["prompt_version"] == "v2"


def test_a_selection_failure_is_logged_with_the_conversation_block(tmp_path: Path, monkeypatch) -> None:
    harness = Harness(tmp_path, monkeypatch, briefings_root=FIXTURES / "no_briefings")

    result = harness.turn("e em 2016?", HISTORY[:1])

    assert result.answer == _NO_DATASET_ANSWER
    assert result.outcome == "none"
    assert result.errored
    assert result.failure is not None
    assert harness.received == []
    (line,) = harness.log_lines()
    assert line["dataset_key"] == "<none>"
    assert line["conversation"]["turn_index"] == 2
    assert line["conversation"]["history_turns_used"] == 1


def test_a_clarification_reply_is_sent_after_the_original_vague_question(
    tmp_path: Path, monkeypatch
) -> None:
    """FR-003 mechanism: the model sees the vague question, its own clarification
    request, and then the short reply as the current message."""
    harness = Harness(tmp_path, monkeypatch)
    clarification = "Poderia especificar qual valor e qual ano deseja consultar?"
    history = [ConversationTurn(question="Me fale sobre o orçamento.", answer=clarification)]

    harness.turn("o valor pago em 2015", history)

    messages, _ = harness.received[0]
    assert isinstance(messages[0], ModelRequest)
    assert [p.content for p in messages[0].parts if isinstance(p, UserPromptPart)] == [
        "Me fale sobre o orçamento."
    ]
    assert isinstance(messages[1], ModelResponse)
    assert [p.content for p in messages[1].parts if isinstance(p, TextPart)] == [clarification]
    assert [p.content for p in messages[2].parts if isinstance(p, UserPromptPart)] == [
        "o valor pago em 2015"
    ]


@pytest.mark.parametrize("limit", [0])
def test_a_zero_limit_sends_no_history(tmp_path: Path, monkeypatch, limit: int) -> None:
    harness = Harness(tmp_path, monkeypatch, history_char_limit=limit)

    harness.turn("e em 2016?", HISTORY)

    messages, _ = harness.received[0]
    assert len(messages) == 1
    assert harness.log_lines()[0]["conversation"]["history_turns_dropped"] == 3
