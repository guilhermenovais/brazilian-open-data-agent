"""Unit tests for ConversationTestsetLoader (008 contracts/conversation-testset.md "Loader rules")."""

import hashlib
import json
from pathlib import Path

import pytest

from testset_runner.conversation_loader import ConversationTestsetLoader
from testset_runner.exceptions import TestsetLoadError


def _write(tmp_path: Path, records) -> Path:
    path = tmp_path / "conversations.json"
    path.write_text(json.dumps(records, ensure_ascii=False))
    return path


def _conversation(conv_id: str = "c1", turns: list[dict] | None = None) -> dict:
    return {
        "id": conv_id,
        "category": "follow-up-year",
        "turns": turns
        or [
            {"message": "Quanto foi pago em 2015?", "expected": "10", "scored": False},
            {"message": "e em 2016?", "expected": "20"},
        ],
    }


def test_a_valid_file_loads_with_the_raw_bytes_hash(tmp_path: Path) -> None:
    path = _write(tmp_path, [_conversation("c1"), _conversation("c2")])

    testset = ConversationTestsetLoader().load(path)

    assert testset.path == str(path)
    assert testset.content_hash == hashlib.sha256(path.read_bytes()).hexdigest()
    assert [c.id for c in testset.conversations] == ["c1", "c2"]
    assert testset.conversations[0].description == ""


def test_a_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(TestsetLoadError):
        ConversationTestsetLoader().load(tmp_path / "missing.json")


def test_invalid_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not json")
    with pytest.raises(TestsetLoadError):
        ConversationTestsetLoader().load(path)


@pytest.mark.parametrize(
    "record",
    [
        {"id": "c", "category": "x", "turns": []},
        {"id": "c", "category": "x", "turns": [{"message": ""}]},
        {"id": "c", "category": "x", "turns": [{"message": "m", "expected_outcome": "maybe"}]},
        {"id": "", "category": "x", "turns": [{"message": "m"}]},
        {"id": "c", "category": "", "turns": [{"message": "m"}]},
    ],
    ids=["empty-turns", "empty-message", "bad-outcome", "empty-id", "empty-category"],
)
def test_an_invalid_record_raises(tmp_path: Path, record: dict) -> None:
    with pytest.raises(TestsetLoadError):
        ConversationTestsetLoader().load(_write(tmp_path, [record]))


def test_duplicate_ids_raise(tmp_path: Path) -> None:
    with pytest.raises(TestsetLoadError):
        ConversationTestsetLoader().load(_write(tmp_path, [_conversation("c"), _conversation("c")]))


def test_a_scored_turn_without_any_expectation_raises(tmp_path: Path) -> None:
    record = _conversation(turns=[{"message": "m", "scored": True}])
    with pytest.raises(TestsetLoadError):
        ConversationTestsetLoader().load(_write(tmp_path, [record]))


def test_scored_defaults(tmp_path: Path) -> None:
    record = _conversation(
        turns=[
            {"message": "a", "expected": "1"},
            {"message": "b", "expected_outcome": "none"},
            {"message": "c"},
            {"message": "d", "expected": "1", "scored": False},
            {"message": "e", "expected_outcome": "full", "scored": True},
        ]
    )

    turns = ConversationTestsetLoader().load(_write(tmp_path, [record])).conversations[0].turns

    assert [t.is_scored for t in turns] == [True, True, False, False, True]
