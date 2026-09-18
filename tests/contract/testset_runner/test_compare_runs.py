"""Contract tests for User Story 2 Acceptance Scenarios (quickstart.md Scenario 6),
per contracts/comparing.md.
"""

import json
from pathlib import Path

from qa_agent.models import QuestionAnsweringResult
from testset_runner.comparator import compare_runs
from testset_runner.models import TargetConfiguration
from testset_runner.runner import run_testset
from testset_runner.store import JsonFileRunStore

REPO_ROOT = Path(__file__).parent.parent.parent.parent
BUNDLED_TESTSET = REPO_ROOT / "data" / "testsets" / "orcamentos-aeb-csv.json"


class ScriptedAnswerer:
    """Answers every question with its own `expected` value, except `wrong_ns`,
    which get a deliberately incorrect numeric answer instead."""

    def __init__(self, testset_path: Path, *, wrong_ns: frozenset[int] = frozenset()) -> None:
        records = json.loads(testset_path.read_bytes())
        self._by_question_text = {record["question"]: record for record in records}
        self._wrong_ns = wrong_ns

    def answer(self, question: str) -> QuestionAnsweringResult:
        record = self._by_question_text[question]
        if record["n"] in self._wrong_ns:
            answer = "A resposta é 1."
        else:
            answer = f"A resposta é {record['expected']}."
        return QuestionAnsweringResult(
            answer=answer,
            dataset_key="orcamentos-aeb-csv",
            outcome="full",
            steps=[],
            errored=False,
        )


def test_comparison_accounts_for_every_question_not_just_the_changed_ones(
    tmp_path: Path,
) -> None:
    store = JsonFileRunStore(tmp_path)
    run_a = run_testset(
        BUNDLED_TESTSET,
        TargetConfiguration(model_name="model-a"),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET, wrong_ns=frozenset({1})),
        store=store,
    )
    run_b = run_testset(
        BUNDLED_TESTSET,
        TargetConfiguration(model_name="model-b"),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET),
        store=store,
    )

    comparison = compare_runs(
        f"{tmp_path}/{run_a.run_id}.json", f"{tmp_path}/{run_b.run_id}.json", store=store
    )

    assert len(comparison.entries) == 50
    assert sum(comparison.summary.values()) == 50
    entry_1 = next(e for e in comparison.entries if e.n == 1)
    assert entry_1.status_a == "not_matched"
    assert entry_1.status_b == "matched"
    assert entry_1.transition == "newly_passing"


def test_comparison_states_each_runs_target_configuration_directly(tmp_path: Path) -> None:
    store = JsonFileRunStore(tmp_path)
    run_a = run_testset(
        BUNDLED_TESTSET,
        TargetConfiguration(model_name="model-a", base_url="http://localhost:8000/v1"),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET),
        store=store,
    )
    run_b = run_testset(
        BUNDLED_TESTSET,
        TargetConfiguration(model_name="model-b"),
        answerer=ScriptedAnswerer(BUNDLED_TESTSET),
        store=store,
    )

    comparison = compare_runs(
        f"{tmp_path}/{run_a.run_id}.json", f"{tmp_path}/{run_b.run_id}.json", store=store
    )

    assert comparison.run_a.model_name == "model-a"
    assert comparison.run_a.base_url == "http://localhost:8000/v1"
    assert comparison.run_b.model_name == "model-b"
    assert comparison.run_b.base_url is None
