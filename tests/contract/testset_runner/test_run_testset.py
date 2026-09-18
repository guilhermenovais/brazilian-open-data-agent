"""Contract tests for User Story 1 Acceptance Scenarios (quickstart.md Scenarios 1-4)
and User Story 3 (differing target configuration), per contracts/running.md.
"""

import json
from pathlib import Path

from qa_agent.models import QuestionAnsweringResult
from testset_runner.models import TargetConfiguration
from testset_runner.runner import run_testset
from testset_runner.store import JsonFileRunStore

REPO_ROOT = Path(__file__).parent.parent.parent.parent
BUNDLED_TESTSET = REPO_ROOT / "data" / "testsets" / "orcamentos-aeb-csv.json"
DATASET_KEY = "orcamentos-aeb-csv"
UNKNOWN_DATASET_KEY = "<none>"


class ScriptedAnswerer:
    """Returns the testset's own `expected` value verbatim as the answer, so numeric
    questions auto-grade "matched" and non-numeric ones become "needs_review" — except
    for `n`s listed in `fail_ns`, which come back `errored=True`."""

    def __init__(self, testset_path: Path, *, fail_ns: frozenset[int] = frozenset()) -> None:
        records = json.loads(testset_path.read_bytes())
        self._by_question_text = {record["question"]: record for record in records}
        self._fail_ns = fail_ns

    def answer(self, question: str) -> QuestionAnsweringResult:
        record = self._by_question_text[question]
        if record["n"] in self._fail_ns:
            return QuestionAnsweringResult(
                answer="Não foi possível processar a pergunta no momento.",
                dataset_key=DATASET_KEY,
                outcome="none",
                steps=[],
                errored=True,
            )
        return QuestionAnsweringResult(
            answer=f"A resposta é {record['expected']}.",
            dataset_key=DATASET_KEY,
            outcome="full",
            steps=[],
            errored=False,
        )


def _target(model_name: str = "fake", base_url: str | None = None) -> TargetConfiguration:
    return TargetConfiguration(model_name=model_name, base_url=base_url)


def test_full_run_produces_one_report_covering_every_question(tmp_path: Path) -> None:
    run = run_testset(
        BUNDLED_TESTSET,
        _target(),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET),
        store=JsonFileRunStore(tmp_path),
    )

    assert len(run.results) == 50
    assert run.summary.total_questions == 50
    assert (tmp_path / f"{run.run_id}.json").exists()


def test_each_question_result_carries_full_per_question_detail(tmp_path: Path) -> None:
    run = run_testset(
        BUNDLED_TESTSET,
        _target(),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET),
        store=JsonFileRunStore(tmp_path),
    )

    result = run.results[0]
    assert result.question
    assert result.expected
    assert result.actual_answer
    assert result.agent_outcome in ("full", "partial", "none")
    assert result.dataset_key == DATASET_KEY
    assert isinstance(result.steps, list)
    assert result.match_status in ("matched", "not_matched", "needs_review", "errored")


def test_numeric_expected_values_are_auto_graded(tmp_path: Path) -> None:
    run = run_testset(
        BUNDLED_TESTSET,
        _target(),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET),
        store=JsonFileRunStore(tmp_path),
    )

    numeric_result = next(r for r in run.results if r.n == 1)
    assert numeric_result.match_status == "matched"

    tolerant_result = next(r for r in run.results if r.n == 30)
    assert tolerant_result.expected.startswith("~")
    assert tolerant_result.match_status == "matched"


def test_non_numeric_expected_values_are_always_needs_review(tmp_path: Path) -> None:
    run = run_testset(
        BUNDLED_TESTSET,
        _target(),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET),
        store=JsonFileRunStore(tmp_path),
    )

    composite_result = next(r for r in run.results if r.n == 45)
    assert "/" in composite_result.expected
    assert composite_result.match_status == "needs_review"

    descriptive_result = next(r for r in run.results if r.n == 48)
    assert descriptive_result.match_status == "needs_review"


def test_a_single_questions_failure_does_not_abort_the_run(tmp_path: Path) -> None:
    run = run_testset(
        BUNDLED_TESTSET,
        _target(),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET, fail_ns=frozenset({7})),
        store=JsonFileRunStore(tmp_path),
    )

    assert len(run.results) == 50
    assert next(r for r in run.results if r.n == 7).match_status == "errored"
    assert all(r.match_status != "errored" for r in run.results if r.n != 7)


def test_target_unreachable_when_every_eligible_question_errors(tmp_path: Path) -> None:
    all_n = {record["n"] for record in json.loads(BUNDLED_TESTSET.read_bytes())}
    run = run_testset(
        BUNDLED_TESTSET,
        _target(),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET, fail_ns=frozenset(all_n)),
        store=JsonFileRunStore(tmp_path),
    )
    assert run.summary.target_unreachable is True

    partial_run = run_testset(
        BUNDLED_TESTSET,
        _target(),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET, fail_ns=frozenset({7})),
        store=JsonFileRunStore(tmp_path),
    )
    assert partial_run.summary.target_unreachable is False


def test_two_runs_differing_only_in_target_both_complete_and_record_their_target(
    tmp_path: Path,
) -> None:
    run_a = run_testset(
        BUNDLED_TESTSET,
        _target(model_name="model-a"),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET),
        store=JsonFileRunStore(tmp_path),
    )
    run_b = run_testset(
        BUNDLED_TESTSET,
        _target(model_name="model-b", base_url="http://localhost:8000/v1"),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET),
        store=JsonFileRunStore(tmp_path),
    )

    assert run_a.target.model_name == "model-a"
    assert run_a.target.base_url is None
    assert run_b.target.model_name == "model-b"
    assert run_b.target.base_url == "http://localhost:8000/v1"
