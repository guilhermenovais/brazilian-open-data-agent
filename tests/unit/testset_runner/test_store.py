"""Unit tests for JsonFileRunStore (research.md §7)."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from testset_runner.exceptions import RunLoadError
from testset_runner.models import (
    QuestionResult,
    RunSummary,
    TargetConfiguration,
    Testset,
    TestRun,
)
from testset_runner.store import JsonFileRunStore


def _sample_run(run_id: str = "20260918T153000000000Z") -> TestRun:
    testset = Testset(path="fixture.json", content_hash="abc123", questions=[])
    result = QuestionResult(
        n=1,
        question="Quanto?",
        expected="10",
        category="single-lookup",
        actual_answer="10",
        agent_outcome="full",
        dataset_key="sample",
        steps=[],
        match_status="matched",
    )
    summary = RunSummary(
        total_questions=1,
        match_rate=1.0,
        by_status={"matched": 1},
        by_category={},
        target_unreachable=False,
    )
    return TestRun(
        run_id=run_id,
        created_at=datetime.now(timezone.utc),
        testset=testset,
        target=TargetConfiguration(model_name="fake"),
        results=[result],
        summary=summary,
    )


def test_save_writes_exactly_one_json_file_named_by_run_id(tmp_path: Path) -> None:
    store = JsonFileRunStore(tmp_path)
    run = _sample_run()

    store.save(run)

    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    assert files[0].name == f"{run.run_id}.json"


def test_load_round_trips_an_equal_test_run(tmp_path: Path) -> None:
    store = JsonFileRunStore(tmp_path)
    run = _sample_run()
    path = store.save(run)

    loaded = store.load(path)

    assert loaded == run


def test_load_raises_run_load_error_for_a_missing_path(tmp_path: Path) -> None:
    store = JsonFileRunStore(tmp_path)
    with pytest.raises(RunLoadError):
        store.load(tmp_path / "does-not-exist.json")


def test_load_raises_run_load_error_for_a_malformed_file(tmp_path: Path) -> None:
    store = JsonFileRunStore(tmp_path)
    malformed = tmp_path / "malformed.json"
    malformed.write_text("not json")
    with pytest.raises(RunLoadError):
        store.load(malformed)
