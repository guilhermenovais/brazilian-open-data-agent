"""Contract tests for discovery, one per US1 Acceptance Scenario + FR-012a
(contracts/discovery.md)."""

from pathlib import Path

import pytest

from data_access.capabilities import discover_data_sources
from data_access.dataset import Dataset
from data_access.exceptions import IdentifierCollisionError

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sample_dataset"


def test_us1_1_all_csv_json_sources_listed_with_identifier_and_format() -> None:
    dataset = Dataset(FIXTURES)
    result = discover_data_sources(dataset)
    by_identifier = {s.identifier: s for s in result.sources}
    assert by_identifier["customers.csv"].format == "csv"
    assert by_identifier["products.json"].format == "json"
    assert by_identifier["orders/2024/sales.csv"].format == "csv"


def test_us1_2_non_data_files_excluded() -> None:
    dataset = Dataset(FIXTURES)
    result = discover_data_sources(dataset)
    assert all(s.identifier != "README.md" for s in result.sources)


def test_us1_3_empty_dataset_returns_empty_list_not_error(tmp_path: Path) -> None:
    dataset = Dataset(tmp_path)
    result = discover_data_sources(dataset)
    assert result.sources == []


def test_us1_4_unparseable_source_listed_unreadable_others_unaffected() -> None:
    dataset = Dataset(FIXTURES)
    result = discover_data_sources(dataset)
    by_identifier = {s.identifier: s for s in result.sources}
    assert by_identifier["broken.csv"].readable is False
    assert by_identifier["customers.csv"].readable is True


def test_us1_5_nested_subfolders_flattened_with_relative_path_identifier() -> None:
    dataset = Dataset(FIXTURES)
    result = discover_data_sources(dataset)
    identifiers = {s.identifier for s in result.sources}
    assert "orders/2024/sales.csv" in identifiers


def test_fr012a_colliding_identifiers_fail_whole_call(tmp_path: Path) -> None:
    (tmp_path / "data.csv").write_text("a,b\n1,2\n")
    (tmp_path / "DATA.csv").write_text("a,b\n3,4\n")
    dataset = Dataset(tmp_path)
    with pytest.raises(IdentifierCollisionError):
        discover_data_sources(dataset)
