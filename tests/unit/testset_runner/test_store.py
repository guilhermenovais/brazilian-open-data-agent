"""Unit tests for JsonFileRunStore (research.md §7)."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from testset_runner.conversation_models import (
    ConversationResult,
    ConversationRun,
    ConversationRunSummary,
    ConversationTestset,
    TurnResult,
)
from testset_runner.exceptions import RunLoadError
from testset_runner.models import (
    QuestionResult,
    RetryPolicy,
    RunSummary,
    TargetConfiguration,
    Testset,
    TestRun,
)
from testset_runner.store import JsonFileConversationRunStore, JsonFileRunStore

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


# --- 008: JsonFileConversationRunStore ---------------------------------------------


def _sample_conversation_run(run_id: str = "20260925T120000000000Z") -> ConversationRun:
    turn = TurnResult(
        turn_index=1,
        message="Quanto?",
        expected="10",
        actual_answer="10",
        agent_outcome="full",
        dataset_key="sample",
        steps=[],
        history_turns_sent=0,
        history_turns_used=0,
        scored=True,
        status="matched",
        attempts=1,
    )
    summary = ConversationRunSummary(
        total_conversations=1,
        total_turns=1,
        scored_turns=1,
        match_rate=1.0,
        by_status={"matched": 1},
        by_category={},
        turns_with_ungrounded_figures=0,
        target_unreachable=False,
    )
    return ConversationRun(
        run_id=run_id,
        created_at=datetime.now(timezone.utc),
        testset=ConversationTestset(path="c.json", content_hash="abc", conversations=[]),
        target=TargetConfiguration(model_name="fake"),
        retry_policy=RetryPolicy(),
        history_char_limit=16_000,
        prompt_version="v2",
        results=[ConversationResult(conversation_id="c1", category="cat", turns=[turn])],
        summary=summary,
    )


def test_conversation_store_round_trips_a_run(tmp_path: Path) -> None:
    store = JsonFileConversationRunStore(tmp_path)
    run = _sample_conversation_run()

    path = store.save(run)

    assert Path(path).name == f"{run.run_id}.json"
    assert store.load(path) == run


def test_conversation_store_rejects_a_standalone_run_file(tmp_path: Path) -> None:
    standalone_path = JsonFileRunStore(tmp_path).save(_sample_run())
    with pytest.raises(RunLoadError):
        JsonFileConversationRunStore(tmp_path).load(standalone_path)


def test_conversation_store_raises_for_a_missing_path(tmp_path: Path) -> None:
    with pytest.raises(RunLoadError):
        JsonFileConversationRunStore(tmp_path).load(tmp_path / "nope.json")
