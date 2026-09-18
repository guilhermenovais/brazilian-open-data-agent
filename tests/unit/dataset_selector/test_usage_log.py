"""Unit tests for JsonlSelectionLogger (JSONL append, one line per call — FR-007)."""

import json
from datetime import datetime, timezone
from pathlib import Path

from dataset_selector.models import DatasetSelectionLogEntry
from dataset_selector.usage_log import JsonlSelectionLogger


def test_log_appends_one_line_per_call(tmp_path: Path) -> None:
    log_path = tmp_path / "nested" / "log.jsonl"
    logger = JsonlSelectionLogger(log_path)
    entry_1 = DatasetSelectionLogEntry(
        question="Q1", dataset_key="key-1", timestamp=datetime.now(timezone.utc)
    )
    entry_2 = DatasetSelectionLogEntry(
        question="Q2", dataset_key="key-2", timestamp=datetime.now(timezone.utc)
    )

    logger.log(entry_1)
    logger.log(entry_2)

    lines = log_path.read_text().splitlines()
    assert len(lines) == 2


def test_log_creates_parent_directory_if_missing(tmp_path: Path) -> None:
    log_path = tmp_path / "does" / "not" / "exist" / "log.jsonl"
    logger = JsonlSelectionLogger(log_path)
    entry = DatasetSelectionLogEntry(
        question="Q", dataset_key="key", timestamp=datetime.now(timezone.utc)
    )

    logger.log(entry)

    assert log_path.exists()


def test_log_entry_round_trips_through_json(tmp_path: Path) -> None:
    log_path = tmp_path / "log.jsonl"
    logger = JsonlSelectionLogger(log_path)
    entry = DatasetSelectionLogEntry(
        question="Some question?",
        dataset_key="some-key",
        timestamp=datetime.now(timezone.utc),
    )

    logger.log(entry)

    line = log_path.read_text().splitlines()[0]
    data = json.loads(line)
    assert data["question"] == entry.question
    assert data["dataset_key"] == entry.dataset_key
    assert datetime.fromisoformat(data["timestamp"]) == entry.timestamp
