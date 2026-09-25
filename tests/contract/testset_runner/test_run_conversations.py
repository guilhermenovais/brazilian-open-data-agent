"""Contract tests for run_conversations (008 contracts/conversation-testset.md), driven by a
fake `ConversationalAnswerer` that records every `(message, context)` it receives."""

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from data_access.text_matching import TextMatchingConfig
from qa_agent.conversation import ConversationContext
from qa_agent.models import FailureDetail, QuestionAnsweringResult, RetrievalStep
from testset_runner.conversation_models import ConversationRun
from testset_runner.conversation_runner import run_conversations
from testset_runner.exceptions import TestsetLoadError
from testset_runner.models import RetryPolicy, TargetConfiguration
from testset_runner.store import JsonFileConversationRunStore

DATASET_KEY = "orcamentos-aeb-csv"
Responder = Callable[[str, ConversationContext], QuestionAnsweringResult]


def _ok(answer: str, *, outcome: str = "full", steps: list[RetrievalStep] | None = None):
    return QuestionAnsweringResult(
        answer=answer, dataset_key=DATASET_KEY, outcome=outcome, steps=steps or []  # type: ignore[arg-type]
    )


def _step(summary: str) -> RetrievalStep:
    return RetrievalStep(tool_name="aggregate_rows", arguments={}, result_summary=summary)


class RecordingAnswerer:
    def __init__(self, respond: Responder | None = None) -> None:
        self._respond = respond or (lambda message, context: _ok(f"resposta para {message}"))
        self.calls: list[tuple[str, ConversationContext]] = []

    def answer_turn(self, message: str, context: ConversationContext) -> QuestionAnsweringResult:
        self.calls.append((message, context))
        return self._respond(message, context)


class RecordingStore:
    def __init__(self) -> None:
        self.saved: list[ConversationRun] = []

    def save(self, run: ConversationRun) -> str:
        self.saved.append(run)
        return run.run_id

    def load(self, path: str | Path) -> ConversationRun:
        raise NotImplementedError


def _write(tmp_path: Path, conversations: list[dict]) -> Path:
    path = tmp_path / "conversations.json"
    path.write_text(json.dumps(conversations, ensure_ascii=False))
    return path


def _run(
    tmp_path: Path,
    conversations: list[dict],
    answerer,
    *,
    limit: int = 16_000,
    store=None,
    **kwargs,
):
    return run_conversations(
        _write(tmp_path, conversations),
        TargetConfiguration(model_name="fake"),
        answerer=answerer,
        store=store or RecordingStore(),
        history_char_limit=limit,
        retry_policy=RetryPolicy(max_attempts=1),
        sleep=lambda _seconds: None,
        **kwargs,
    )


TWO_CONVERSATIONS = [
    {
        "id": "a",
        "category": "follow-up-year",
        "turns": [
            {"message": "Quanto foi pago em 2015?", "scored": False},
            {"message": "e em 2016?"},
            {"message": "e em 2017?"},
        ],
    },
    {"id": "b", "category": "fresh-chat-follow-up", "turns": [{"message": "e em 2016?"}]},
]


def test_history_grows_with_the_answerers_actual_answers(tmp_path: Path) -> None:
    answerer = RecordingAnswerer()
    run = _run(tmp_path, TWO_CONVERSATIONS, answerer)

    contexts = [context for _, context in answerer.calls]
    assert [c.turn_index for c in contexts] == [1, 2, 3, 1]
    assert contexts[0].history == []
    assert [(t.question, t.answer) for t in contexts[2].history] == [
        ("Quanto foi pago em 2015?", "resposta para Quanto foi pago em 2015?"),
        ("e em 2016?", "resposta para e em 2016?"),
    ]
    assert contexts[0].conversation_id == f"{run.run_id}:a"
    assert contexts[3].conversation_id == f"{run.run_id}:b"


def test_every_conversation_starts_from_an_empty_history(tmp_path: Path) -> None:
    """SC-005 isolation: nothing an earlier conversation answered leaks into the next."""
    answerer = RecordingAnswerer()
    _run(tmp_path, TWO_CONVERSATIONS, answerer)

    first_turns = [context for _, context in answerer.calls if context.turn_index == 1]
    assert len(first_turns) == 2
    assert all(context.history == [] for context in first_turns)
    assert first_turns[0].conversation_id != first_turns[1].conversation_id


def test_turns_used_equals_turns_sent_when_the_history_fits(tmp_path: Path) -> None:
    run = _run(tmp_path, TWO_CONVERSATIONS, RecordingAnswerer())

    turns = run.results[0].turns
    assert [t.history_turns_sent for t in turns] == [0, 1, 2]
    assert [t.history_turns_used for t in turns] == [0, 1, 2]


def test_turns_used_is_smaller_with_a_small_history_limit(tmp_path: Path) -> None:
    answerer = RecordingAnswerer(lambda message, context: _ok("x" * 40))
    run = _run(tmp_path, TWO_CONVERSATIONS, answerer, limit=60)

    last = run.results[0].turns[-1]
    assert last.history_turns_sent == 2
    assert last.history_turns_used == 1


def test_an_errored_turn_is_still_appended_and_later_turns_run(tmp_path: Path) -> None:
    failure = FailureDetail(type="ConnectError", message="boom", transient=False)

    def respond(message: str, context: ConversationContext) -> QuestionAnsweringResult:
        if context.turn_index == 1:
            return QuestionAnsweringResult(
                answer="Não foi possível processar a pergunta no momento.",
                dataset_key=DATASET_KEY,
                outcome="none",
                errored=True,
                failure=failure,
            )
        return _ok("ok")

    answerer = RecordingAnswerer(respond)
    run = _run(tmp_path, TWO_CONVERSATIONS[:1], answerer)

    assert len(answerer.calls) == 3
    first = run.results[0].turns[0]
    assert first.status == "errored"
    assert first.failure == failure
    assert first.ungrounded_figures == []
    assert answerer.calls[1][1].history[0].answer == "Não foi possível processar a pergunta no momento."


@pytest.mark.parametrize(
    "turn,answer,outcome,status",
    [
        ({"message": "m", "expected": "42"}, "Foram R$ 42.", "full", "matched"),
        ({"message": "m", "expected": "42", "expected_outcome": "full"}, "R$ 42.", "none", "not_matched"),
        (
            {"message": "m", "expected": "texto livre", "expected_outcome": "full"},
            "R$ 42.",
            "full",
            "needs_review",
        ),
        ({"message": "m", "expected_outcome": "none"}, "Pergunta vaga.", "none", "matched"),
        ({"message": "m", "expected": "42", "scored": False}, "R$ 7.", "full", "unscored"),
        ({"message": "m"}, "R$ 7.", "full", "unscored"),
    ],
    ids=["numeric-match", "outcome-mismatch", "needs-review-wins", "outcome-only", "context", "no-expectation"],
)
def test_turn_scoring(tmp_path: Path, turn: dict, answer: str, outcome: str, status: str) -> None:
    answerer = RecordingAnswerer(lambda message, context: _ok(answer, outcome=outcome))
    run = _run(tmp_path, [{"id": "c", "category": "cat", "turns": [turn]}], answerer)

    assert run.results[0].turns[0].status == status


def test_ungrounded_figures_are_recorded_per_turn(tmp_path: Path) -> None:
    answerer = RecordingAnswerer(
        lambda message, context: _ok("Pago: R$ 42; antes, R$ 99.", steps=[_step('{"value": 42}')])
    )
    run = _run(tmp_path, [{"id": "c", "category": "cat", "turns": [{"message": "m"}]}], answerer)

    assert run.results[0].turns[0].ungrounded_figures == ["99"]
    assert run.summary.turns_with_ungrounded_figures == 1


def test_summary_counts_only_scored_turns_overall_and_by_category(tmp_path: Path) -> None:
    def respond(message: str, context: ConversationContext) -> QuestionAnsweringResult:
        return _ok("R$ 42", outcome="none" if message == "e em 2016?" and context.turn_index == 1 else "full")

    conversations = [
        {
            "id": "a",
            "category": "follow-up-year",
            "turns": [
                {"message": "Quanto em 2015?", "expected": "1", "scored": False},
                {"message": "e em 2016?", "expected": "42"},
            ],
        },
        {
            "id": "b",
            "category": "follow-up-year",
            "turns": [{"message": "Quanto em 2015?", "scored": False}, {"message": "e em 2017?", "expected": "7"}],
        },
        {"id": "c", "category": "fresh-chat-follow-up", "turns": [{"message": "e em 2016?", "expected_outcome": "none"}]},
    ]

    summary = _run(tmp_path, conversations, RecordingAnswerer(respond)).summary

    assert summary.total_conversations == 3
    assert summary.total_turns == 5
    assert summary.scored_turns == 3
    assert summary.match_rate == pytest.approx(2 / 3)
    assert summary.by_status == {"unscored": 2, "matched": 2, "not_matched": 1}
    assert summary.by_category["follow-up-year"].scored_turns == 2
    assert summary.by_category["follow-up-year"].match_rate == pytest.approx(0.5)
    assert summary.by_category["fresh-chat-follow-up"].match_rate == 1.0
    assert summary.target_unreachable is False


def test_an_errored_context_turn_does_not_lower_the_rate(tmp_path: Path) -> None:
    def respond(message: str, context: ConversationContext) -> QuestionAnsweringResult:
        if context.turn_index == 1:
            return QuestionAnsweringResult(
                answer="falhou", dataset_key=DATASET_KEY, outcome="none", errored=True
            )
        return _ok("R$ 42")

    conversations = [
        {
            "id": "a",
            "category": "cat",
            "turns": [{"message": "ctx", "scored": False}, {"message": "m", "expected": "42"}],
        }
    ]
    summary = _run(tmp_path, conversations, RecordingAnswerer(respond)).summary

    assert summary.by_status == {"errored": 1, "matched": 1}
    assert summary.scored_turns == 1
    assert summary.match_rate == 1.0


def test_target_unreachable_when_every_turn_reaching_the_model_errored(tmp_path: Path) -> None:
    def respond(message: str, context: ConversationContext) -> QuestionAnsweringResult:
        return QuestionAnsweringResult(
            answer="falhou",
            dataset_key="<none>" if message == "sem base" else DATASET_KEY,
            outcome="none",
            errored=True,
        )

    conversations = [
        {"id": "a", "category": "cat", "turns": [{"message": "m1"}, {"message": "sem base"}]},
    ]
    assert _run(tmp_path, conversations, RecordingAnswerer(respond)).summary.target_unreachable


def test_the_saved_run_round_trips_through_the_json_store(tmp_path: Path) -> None:
    store = JsonFileConversationRunStore(tmp_path / "runs")
    run = _run(tmp_path, TWO_CONVERSATIONS, RecordingAnswerer(), store=store)

    loaded = store.load(tmp_path / "runs" / f"{run.run_id}.json")

    assert loaded == run
    assert loaded.history_char_limit == 16_000
    assert loaded.prompt_version == "v2"


def test_a_testset_load_error_saves_nothing(tmp_path: Path) -> None:
    store = RecordingStore()
    bad = tmp_path / "bad.json"
    bad.write_text("not json")
    with pytest.raises(TestsetLoadError):
        run_conversations(
            bad,
            TargetConfiguration(model_name="fake"),
            answerer=RecordingAnswerer(),
            store=store,
            history_char_limit=16_000,
        )
    assert store.saved == []


# --- 009: text matching configuration recorded on the run (FR-016) -----------------------


def test_009_text_matching_is_recorded_and_round_trips(tmp_path: Path) -> None:
    config = TextMatchingConfig(max_suggestions=2)
    store = JsonFileConversationRunStore(tmp_path / "runs")
    run = _run(tmp_path, TWO_CONVERSATIONS, RecordingAnswerer(), store=store, text_matching=config)

    assert run.text_matching == config
    assert store.load(tmp_path / "runs" / f"{run.run_id}.json").text_matching == config


def test_009_text_matching_not_given_is_recorded_as_none(tmp_path: Path) -> None:
    assert _run(tmp_path, TWO_CONVERSATIONS, RecordingAnswerer()).text_matching is None
