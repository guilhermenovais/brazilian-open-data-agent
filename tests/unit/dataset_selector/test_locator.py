"""Unit tests for LocalDatasetLocator (data-model.md Errors table, FR-005;
quickstart.md Scenario 4)."""

from pathlib import Path

import pytest

from dataset_selector.exceptions import DatasetNotFoundError
from dataset_selector.locator import LocalDatasetLocator

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "dataset_selector" / "datasets"


def test_locate_existing_key_returns_fixture_folder() -> None:
    locator = LocalDatasetLocator(FIXTURES)
    assert locator.locate("sample-key") == FIXTURES / "sample-key"


def test_locate_missing_key_raises_dataset_not_found_error() -> None:
    locator = LocalDatasetLocator(FIXTURES)
    with pytest.raises(DatasetNotFoundError) as exc_info:
        locator.locate("does-not-exist")
    assert exc_info.value.key == "does-not-exist"
