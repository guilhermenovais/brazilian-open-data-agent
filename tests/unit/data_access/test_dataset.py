"""Unit tests for the Dataset abstraction: identifier derivation, collision
detection, and non-data-file filtering (research.md §11)."""

from pathlib import Path

import pytest

from data_access.dataset import Dataset
from data_access.exceptions import DataSourceNotFoundError, IdentifierCollisionError


def _write(path: Path, content: str = "a,b\n1,2\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


class TestIdentifierDerivation:
    def test_relative_path_identifier_uses_posix_separators(self, tmp_path: Path) -> None:
        _write(tmp_path / "orders" / "2024" / "sales.csv")
        dataset = Dataset(tmp_path)
        identifiers = {s.identifier for s in dataset.list_sources()}
        assert identifiers == {"orders/2024/sales.csv"}

    def test_top_level_file_identifier_has_no_leading_slash(self, tmp_path: Path) -> None:
        _write(tmp_path / "customers.csv")
        dataset = Dataset(tmp_path)
        identifiers = {s.identifier for s in dataset.list_sources()}
        assert identifiers == {"customers.csv"}

    def test_format_derived_from_extension(self, tmp_path: Path) -> None:
        _write(tmp_path / "a.csv")
        _write(tmp_path / "b.json", "[]")
        dataset = Dataset(tmp_path)
        formats = {s.identifier: s.format for s in dataset.list_sources()}
        assert formats == {"a.csv": "csv", "b.json": "json"}


class TestCollisionDetection:
    def test_case_differing_filenames_collide_even_on_case_sensitive_fs(
        self, tmp_path: Path
    ) -> None:
        _write(tmp_path / "data.csv")
        _write(tmp_path / "DATA.csv")
        dataset = Dataset(tmp_path)
        with pytest.raises(IdentifierCollisionError) as exc_info:
            dataset.list_sources()
        physical_paths = exc_info.value.physical_paths
        assert len(physical_paths) == 2
        assert any(p.endswith("data.csv") for p in physical_paths)
        assert any(p.endswith("DATA.csv") for p in physical_paths)

    def test_non_colliding_files_construct_successfully(self, tmp_path: Path) -> None:
        _write(tmp_path / "one.csv")
        _write(tmp_path / "two.csv")
        dataset = Dataset(tmp_path)
        assert len(dataset.list_sources()) == 2


class TestNonDataFileFiltering:
    def test_non_csv_json_files_excluded(self, tmp_path: Path) -> None:
        _write(tmp_path / "data.csv")
        (tmp_path / "README.md").write_text("not a data file")
        dataset = Dataset(tmp_path)
        identifiers = {s.identifier for s in dataset.list_sources()}
        assert identifiers == {"data.csv"}

    def test_empty_dataset_returns_empty_list(self, tmp_path: Path) -> None:
        dataset = Dataset(tmp_path)
        assert dataset.list_sources() == []


class TestResolve:
    def test_resolve_unknown_identifier_raises(self, tmp_path: Path) -> None:
        dataset = Dataset(tmp_path)
        with pytest.raises(DataSourceNotFoundError):
            dataset.resolve("does-not-exist.csv")
