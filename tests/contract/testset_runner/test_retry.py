"""Contract tests for 006 contracts/running-with-retry.md: the bounded per-question retry
loop in `run_testset`, driven by a scripted fake answerer and a recording fake `sleep`.
"""

import json
from pathlib import Path

import pytest

from qa_agent.models import FailureDetail, QuestionAnsweringResult, RetrievalStep
from testset_runner.models import RetryPolicy, TargetConfiguration, TestRun
from testset_runner.runner import _wait, run_testset
from testset_runner.store import JsonFileRunStore

REPO_ROOT = Path(__file__).parent.parent.parent.parent
MINI_TESTSET = REPO_ROOT / "tests" / "fixtures" / "testset_runner" / "mini-testset.json"
RECORDS = json.loads(MINI_TESTSET.read_bytes())
QUESTIONS = [record["question"] for record in RECORDS]
FIRST, SECOND = QUESTIONS[0], QUESTIONS[1]
EXPECTED = {record["question"]: record["expected"] for record in RECORDS}
DATASET_KEY = "orcamentos-aeb-csv"


def _ok(question: str, steps: list[RetrievalStep] | None = None) -> QuestionAnsweringResult:
    return QuestionAnsweringResult(
        answer=f"A resposta é {EXPECTED[question]}.",
        dataset_key=DATASET_KEY,
        outcome="full",
        steps=steps or [],
    )


def _failure(transient: bool = True, retry_after: float | None = None, type_: str = "ConnectError"):
    return FailureDetail(
        type=type_, message="boom", transient=transient, retry_after_seconds=retry_after
    )


def _errored(failure: FailureDetail | None) -> QuestionAnsweringResult:
    return QuestionAnsweringResult(
        answer="Não foi possível processar a pergunta no momento.",
        dataset_key=DATASET_KEY,
        outcome="none",
        errored=True,
        failure=failure,
    )


class ScriptedAnswerer:
    """Pops one scripted result per call for each question; unscripted questions (or an
    exhausted script) answer successfully. Records how often each question was asked."""

    def __init__(self, script: dict[str, list[QuestionAnsweringResult]] | None = None) -> None:
        self._script = {q: list(results) for q, results in (script or {}).items()}
        self.calls: dict[str, int] = {}

    def answer(self, question: str) -> QuestionAnsweringResult:
        self.calls[question] = self.calls.get(question, 0) + 1
        remaining = self._script.get(question)
        if remaining:
            return remaining.pop(0)
        return _ok(question)


class AlwaysFailingAnswerer:
    def __init__(self, failure: FailureDetail | None) -> None:
        self._failure = failure
        self.calls: dict[str, int] = {}

    def answer(self, question: str) -> QuestionAnsweringResult:
        self.calls[question] = self.calls.get(question, 0) + 1
        return _errored(self._failure)


class RecordingSleep:
    def __init__(self) -> None:
        self.waits: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)


class RecordingStore:
    def __init__(self) -> None:
        self.saved: list[TestRun] = []

    def save(self, run: TestRun) -> str:
        self.saved.append(run)
        return run.run_id

    def load(self, path: str | Path) -> TestRun:
        raise NotImplementedError


def _run(answerer, *, policy: RetryPolicy | None = None, sleep=None, store=None) -> TestRun:
    kwargs = {} if policy is None else {"retry_policy": policy}
    return run_testset(
        MINI_TESTSET,
        TargetConfiguration(model_name="fake"),
        answerer=answerer,
        store=store or RecordingStore(),
        sleep=sleep or RecordingSleep(),
        **kwargs,
    )


def _result(run: TestRun, question: str):
    return next(r for r in run.results if r.question == question)


# --- US2 --------------------------------------------------------------------------------


def test_transient_failure_then_success_is_graded_on_the_successful_attempt() -> None:
    steps = [RetrievalStep(tool_name="query", arguments={"x": 1}, result_summary="8351")]
    answerer = ScriptedAnswerer({FIRST: [_errored(_failure()), _ok(FIRST, steps)]})

    result = _result(_run(answerer), FIRST)

    assert result.match_status == "matched"
    assert result.attempts == 2
    assert len(result.failed_attempts) == 1
    assert result.failure is None
    assert result.steps == steps


def test_transient_failure_on_every_attempt_ends_errored_with_every_failure_recorded() -> None:
    failures = [_failure(type_=f"Err{i}") for i in range(3)]
    answerer = ScriptedAnswerer({FIRST: [_errored(f) for f in failures]})

    run = _run(answerer)
    result = _result(run, FIRST)

    assert result.attempts == 3
    assert result.match_status == "errored"
    assert result.failed_attempts == failures
    assert result.failure == result.failed_attempts[-1]
    assert _result(run, SECOND).match_status == "matched"


def test_non_transient_failure_is_not_retried() -> None:
    answerer = ScriptedAnswerer({FIRST: [_errored(_failure(transient=False))]})
    sleep = RecordingSleep()

    result = _result(_run(answerer, sleep=sleep), FIRST)

    assert result.attempts == 1
    assert answerer.calls[FIRST] == 1
    assert sleep.waits == []


def test_errored_result_without_a_failure_is_treated_as_non_transient() -> None:
    answerer = ScriptedAnswerer({FIRST: [_errored(None)]})

    result = _result(_run(answerer), FIRST)

    assert result.attempts == 1
    assert result.failed_attempts == []
    assert result.match_status == "errored"


def test_every_question_failing_once_transiently_ends_with_zero_errored() -> None:
    answerer = ScriptedAnswerer({q: [_errored(_failure())] for q in QUESTIONS})

    run = _run(answerer)

    assert "errored" not in run.summary.by_status
    assert all(r.attempts == 2 for r in run.results)


def test_waits_follow_the_default_backoff() -> None:
    sleep = RecordingSleep()
    _run(ScriptedAnswerer({FIRST: [_errored(_failure())] * 3}), sleep=sleep)
    assert sleep.waits == [2.0, 4.0]


def test_waits_follow_the_backoff_for_a_larger_max_attempts() -> None:
    sleep = RecordingSleep()
    _run(
        ScriptedAnswerer({FIRST: [_errored(_failure())] * 5}),
        policy=RetryPolicy(max_attempts=5),
        sleep=sleep,
    )
    assert sleep.waits == [2.0, 4.0, 8.0, 16.0]


@pytest.mark.parametrize(
    "retry_after,expected_first_wait",
    [(30.0, 30.0), (1.0, 2.0), (500.0, 60.0)],
    ids=["honored", "never-shortens-backoff", "capped"],
)
def test_provider_retry_after_raises_the_wait_up_to_the_cap(
    retry_after: float, expected_first_wait: float
) -> None:
    sleep = RecordingSleep()
    answerer = ScriptedAnswerer({FIRST: [_errored(_failure(retry_after=retry_after))]})

    _run(answerer, sleep=sleep)

    assert sleep.waits == [expected_first_wait]


def test_summary_counts_retried_and_exhausted_questions() -> None:
    answerer = ScriptedAnswerer(
        {
            QUESTIONS[0]: [_errored(_failure())],  # retried, then succeeded
            QUESTIONS[1]: [_errored(_failure())] * 3,  # retried, exhausted
            QUESTIONS[2]: [_errored(_failure(transient=False))],  # errored, not retried
        }
    )

    run = _run(answerer)

    assert run.summary.retried_questions == 2
    assert run.summary.errored_after_retries == 1
    category = RECORDS[1]["type"]
    assert run.summary.by_category[category].errored_after_retries == 1


def test_interrupt_during_a_wait_propagates_and_saves_nothing() -> None:
    def interrupting_sleep(seconds: float) -> None:
        raise KeyboardInterrupt

    store = RecordingStore()
    with pytest.raises(KeyboardInterrupt):
        _run(
            ScriptedAnswerer({FIRST: [_errored(_failure())]}),
            sleep=interrupting_sleep,
            store=store,
        )
    assert store.saved == []


# --- FR-014: the wait computation ----------------------------------------------------


@pytest.mark.parametrize("k", [1, 2, 3, 4])
@pytest.mark.parametrize("retry_after", [None, 5.0, 100.0])
@pytest.mark.parametrize("initial", [0.0, 2.0])
def test_wait_formula(k: int, retry_after: float | None, initial: float) -> None:
    policy = RetryPolicy(initial_wait_seconds=initial)
    expected = min(
        max(initial * policy.backoff_multiplier ** (k - 1), retry_after or 0),
        policy.max_wait_seconds,
    )
    assert _wait(policy, k, retry_after) == expected


# --- US3: a configurable, recorded policy ----------------------------------------------


def test_max_attempts_bounds_the_calls_per_question() -> None:
    answerer = AlwaysFailingAnswerer(_failure())

    _run(answerer, policy=RetryPolicy(max_attempts=2))

    assert set(answerer.calls) == set(QUESTIONS)
    assert all(count <= 2 for count in answerer.calls.values())


def test_max_attempts_one_disables_retry() -> None:
    answerer = AlwaysFailingAnswerer(_failure())
    sleep = RecordingSleep()

    run = _run(answerer, policy=RetryPolicy(max_attempts=1), sleep=sleep)

    assert all(r.attempts == 1 for r in run.results)
    assert sleep.waits == []


def test_the_policy_is_recorded_on_the_run_and_persisted(tmp_path: Path) -> None:
    policy = RetryPolicy(max_attempts=4)
    store = JsonFileRunStore(tmp_path)

    run = _run(ScriptedAnswerer(), policy=policy, store=store)

    assert run.retry_policy == policy
    assert store.load(tmp_path / f"{run.run_id}.json").retry_policy == policy
