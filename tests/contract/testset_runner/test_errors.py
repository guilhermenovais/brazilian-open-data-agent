"""Contract tests for whole-run/whole-comparison failure translation
(contracts/errors.md, quickstart.md Scenarios 5 and 7).
"""

import json
from pathlib import Path

import pytest

from qa_agent.models import QuestionAnsweringResult
from testset_runner.comparator import compare_runs
from testset_runner.exceptions import IncompatibleRunsError, RunLoadError, TestsetLoadError
from testset_runner.models import TargetConfiguration
from testset_runner.runner import run_testset
from testset_runner.store import JsonFileRunStore

FIXTURES_ROOT = Path(__file__).parent.parent.parent / "fixtures" / "testset_runner"
MISSING_EXPECTED_FIELD = FIXTURES_ROOT / "missing-expected-field.json"
MINI_TESTSET = FIXTURES_ROOT / "mini-testset.json"


class ScriptedAnswerer:
    def __init__(self, testset_path: Path) -> None:
        records = json.loads(testset_path.read_bytes())
        self._by_question_text = {record["question"]: record for record in records}

    def answer(self, question: str) -> QuestionAnsweringResult:
        record = self._by_question_text[question]
        return QuestionAnsweringResult(
            answer=f"A resposta é {record['expected']}.",
            dataset_key="orcamentos-aeb-csv",
            outcome="full",
            steps=[],
            errored=False,
        )


def test_missing_expected_field_fails_fast_before_any_question_runs(tmp_path: Path) -> None:
    class ExplodingAnswerer:
        def answer(self, question: str) -> QuestionAnsweringResult:
            raise AssertionError("answerer.answer must not be called when loading fails")

    with pytest.raises(TestsetLoadError):
        run_testset(
            MISSING_EXPECTED_FIELD,
            TargetConfiguration(model_name="fake"),
            answerer=ExplodingAnswerer(),
            store=JsonFileRunStore(tmp_path),
        )

    assert list(tmp_path.glob("*.json")) == []


def test_comparing_runs_from_edited_testset_content_is_rejected(tmp_path: Path) -> None:
    store = JsonFileRunStore(tmp_path)

    run_a = run_testset(
        MINI_TESTSET,
        TargetConfiguration(model_name="model-a"),
        answerer=ScriptedAnswerer(MINI_TESTSET),
        store=store,
    )

    edited_testset = tmp_path / "mini-testset-edited.json"
    records = json.loads(MINI_TESTSET.read_bytes())
    records[0]["expected"] = "999999"
    edited_testset.write_text(json.dumps(records, ensure_ascii=False))

    run_b = run_testset(
        edited_testset,
        TargetConfiguration(model_name="model-b"),
        answerer=ScriptedAnswerer(edited_testset),
        store=store,
    )

    with pytest.raises(IncompatibleRunsError):
        compare_runs(
            f"{tmp_path}/{run_a.run_id}.json",
            f"{tmp_path}/{run_b.run_id}.json",
            store=store,
        )


def test_compare_runs_raises_run_load_error_for_a_bad_path(tmp_path: Path) -> None:
    store = JsonFileRunStore(tmp_path)
    run = run_testset(
        MINI_TESTSET,
        TargetConfiguration(model_name="model-a"),
        answerer=ScriptedAnswerer(MINI_TESTSET),
        store=store,
    )

    with pytest.raises(RunLoadError):
        compare_runs(
            f"{tmp_path}/{run.run_id}.json",
            f"{tmp_path}/does-not-exist.json",
            store=store,
        )

    malformed = tmp_path / "malformed.json"
    malformed.write_text("not json")
    with pytest.raises(RunLoadError):
        compare_runs(f"{tmp_path}/{run.run_id}.json", str(malformed), store=store)
