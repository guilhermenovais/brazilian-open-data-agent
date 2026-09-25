"""Unit tests for TestsetLoader (data-model.md's validation rules)."""

import hashlib
from pathlib import Path

import pytest

from testset_runner.exceptions import TestsetLoadError
from testset_runner.loader import TestsetLoader

FIXTURES_ROOT = Path(__file__).parent.parent.parent / "fixtures" / "testset_runner"
MINI_TESTSET = FIXTURES_ROOT / "mini-testset.json"
MISSING_EXPECTED_FIELD = FIXTURES_ROOT / "missing-expected-field.json"
DUPLICATE_N = FIXTURES_ROOT / "duplicate-n.json"


def test_valid_schema_loads_successfully() -> None:
    testset = TestsetLoader().load(MINI_TESTSET)
    assert len(testset.questions) == 5
    assert testset.path == str(MINI_TESTSET)


def test_content_hash_is_a_stable_sha256_hex_digest_of_the_raw_bytes() -> None:
    testset = TestsetLoader().load(MINI_TESTSET)
    expected_hash = hashlib.sha256(MINI_TESTSET.read_bytes()).hexdigest()
    assert testset.content_hash == expected_hash

    reloaded = TestsetLoader().load(MINI_TESTSET)
    assert reloaded.content_hash == testset.content_hash


def test_duplicate_n_raises_testset_load_error() -> None:
    with pytest.raises(TestsetLoadError):
        TestsetLoader().load(DUPLICATE_N)


def test_missing_expected_field_raises_testset_load_error() -> None:
    with pytest.raises(TestsetLoadError):
        TestsetLoader().load(MISSING_EXPECTED_FIELD)


def test_missing_file_raises_testset_load_error(tmp_path: Path) -> None:
    with pytest.raises(TestsetLoadError):
        TestsetLoader().load(tmp_path / "does-not-exist.json")


# --- 008: expected_outcome ------------------------------------------------------------

INVALID_EXPECTED_OUTCOME = FIXTURES_ROOT / "invalid-expected-outcome.json"
BUNDLED_TESTSET = (
    Path(__file__).parent.parent.parent.parent / "data" / "testsets" / "orcamentos-aeb-csv.json"
)


def test_008_invalid_expected_outcome_is_refused() -> None:
    with pytest.raises(TestsetLoadError) as exc_info:
        TestsetLoader().load(INVALID_EXPECTED_OUTCOME)
    message = str(exc_info.value)
    assert "4.expected_outcome" in message
    assert "maybe" in message


def test_008_expected_outcome_defaults_to_none() -> None:
    testset = TestsetLoader().load(MINI_TESTSET)
    assert all(q.expected_outcome is None for q in testset.questions)


def test_008_us3_7_bundled_testset_expected_outcomes() -> None:
    testset = TestsetLoader().load(BUNDLED_TESTSET)
    by_n = {q.n: q.expected_outcome for q in testset.questions}
    assert by_n[48] == "none"
    assert by_n[49] == "needs_clarification"
    assert by_n[50] == "none"
    others = {n: outcome for n, outcome in by_n.items() if n not in (48, 49, 50)}
    assert len(others) == 47
    assert all(outcome is None for outcome in others.values())
