"""Unit tests for FileBriefingSource (list_keys()/get(), BriefingNotFoundError)."""

from pathlib import Path

import pytest

from dataset_selector.briefing import FileBriefingSource
from dataset_selector.exceptions import BriefingNotFoundError

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "dataset_selector" / "briefings"


def test_list_keys_returns_sample_key() -> None:
    source = FileBriefingSource(FIXTURES)
    assert source.list_keys() == ["sample-key"]


def test_get_returns_fixture_file_exact_text() -> None:
    source = FileBriefingSource(FIXTURES)
    assert source.get("sample-key") == (FIXTURES / "sample-key.md").read_text()


def test_get_missing_key_raises_briefing_not_found_error() -> None:
    source = FileBriefingSource(FIXTURES)
    with pytest.raises(BriefingNotFoundError) as exc_info:
        source.get("missing-key")
    assert exc_info.value.key == "missing-key"
