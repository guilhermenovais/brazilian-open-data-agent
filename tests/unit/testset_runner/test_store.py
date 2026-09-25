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

PRE_006_RUN = Path(__file__).parent.parent.parent / "fixtures" / "testset_runner" / "pre-006-run.json"


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


def test_a_pre_006_run_file_still_loads_with_new_fields_unrecorded(tmp_path: Path) -> None:
    run = JsonFileRunStore(tmp_path).load(PRE_006_RUN)

    assert any(r.match_status == "errored" for r in run.results)
    assert all(r.failure is None for r in run.results)
    assert run.summary.errored_by_failure_type is None


# --- 008: backward compatibility on committed run fixtures (SC-006, SC-007) ------------

SAMPLE_008_RUN = PRE_006_RUN.parent / "008-sample-run.json"


@pytest.mark.parametrize("fixture", [SAMPLE_008_RUN, PRE_006_RUN], ids=["008-sample", "pre-006"])
def test_008_sample_run_fixture_loads(fixture: Path) -> None:
    run = JsonFileRunStore(fixture.parent).load(fixture)
    assert run.results
    assert all(r.expected_outcome is None for r in run.results)
    assert run.target.prompt_version is None
    assert run.briefing_fingerprints is None


def test_008_sc007_regrade_is_unchanged() -> None:
    """Only the real-run fixture: pre-006-run.json is hand-written, and its n=5 carries a
    `match_status` the matcher never produced (a non-numeric `expected` is always
    `needs_review`, before and after 008)."""
    from testset_runner.matcher import DeterministicMatcher

    run = JsonFileRunStore(SAMPLE_008_RUN.parent).load(SAMPLE_008_RUN)
    matcher = DeterministicMatcher()
    graded = [r for r in run.results if r.match_status != "errored"]
    assert graded
    for r in graded:
        assert matcher.grade(r.expected, r.actual_answer) == r.match_status, f"n={r.n}"
