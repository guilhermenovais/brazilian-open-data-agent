"""Unit tests for JsonlRunLogger (JSONL append, one line per call — FR-013)."""

import json
from datetime import datetime, timezone
from pathlib import Path

from qa_agent.models import AgentRunLogEntry
from qa_agent.run_log import JsonlRunLogger


def test_log_appends_one_line_per_call(tmp_path: Path) -> None:
    log_path = tmp_path / "nested" / "log.jsonl"
    logger = JsonlRunLogger(log_path)
    entry_1 = AgentRunLogEntry(
        question="Q1", dataset_key="key-1", outcome="full", timestamp=datetime.now(timezone.utc)
    )
    entry_2 = AgentRunLogEntry(
        question="Q2", dataset_key="key-2", outcome="none", timestamp=datetime.now(timezone.utc)
    )

    logger.log(entry_1)
    logger.log(entry_2)

    lines = log_path.read_text().splitlines()
    assert len(lines) == 2


def test_log_creates_parent_directory_if_missing(tmp_path: Path) -> None:
    log_path = tmp_path / "does" / "not" / "exist" / "log.jsonl"
    logger = JsonlRunLogger(log_path)
    entry = AgentRunLogEntry(
        question="Q", dataset_key="key", outcome="partial", timestamp=datetime.now(timezone.utc)
    )

    logger.log(entry)

    assert log_path.exists()


def test_log_entry_contains_required_keys(tmp_path: Path) -> None:
    log_path = tmp_path / "log.jsonl"
    logger = JsonlRunLogger(log_path)
    entry = AgentRunLogEntry(
        question="Some question?",
        dataset_key="some-key",
        outcome="full",
        timestamp=datetime.now(timezone.utc),
    )

    logger.log(entry)

    line = log_path.read_text().splitlines()[0]
    data = json.loads(line)
    assert {"question", "dataset_key", "outcome", "timestamp"} <= data.keys()
    assert data["question"] == entry.question
    assert data["dataset_key"] == entry.dataset_key
    assert data["outcome"] == entry.outcome
