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
