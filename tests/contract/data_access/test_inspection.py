"""Contract tests for schema inspection, US2.1-US2.5 (contracts/inspection.md)."""

from pathlib import Path

import pytest

from data_access.capabilities import SAMPLE_SIZE_CAP, inspect_schema
from data_access.dataset import Dataset
from data_access.exceptions import DataSourceNotFoundError, UnreadableSourceError

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "data_access" / "sample_dataset"


def test_us2_1_large_csv_capped_sample_all_field_names(tmp_path: Path) -> None:
    lines = ["id,value"] + [f"{i},{i * 10}" for i in range(10_000)]
    (tmp_path / "big.csv").write_text("\n".join(lines) + "\n")
    dataset = Dataset(tmp_path)

    result = inspect_schema(dataset, "big.csv")

    assert {f.name for f in result.fields} == {"id", "value"}
    assert len(result.sample) == SAMPLE_SIZE_CAP


def test_us2_2_heterogeneous_json_union_of_fields() -> None:
    dataset = Dataset(FIXTURES)
    result = inspect_schema(dataset, "products.json")
    field_names = {f.name for f in result.fields}
    assert field_names == {"id", "name", "price", "category"}


def test_us2_3_brazilian_formatted_value_shown_unchanged_and_numeric_like() -> None:
    dataset = Dataset(FIXTURES)
    result = inspect_schema(dataset, "orders/2024/sales.csv")
    amount_field = next(f for f in result.fields if f.name == "amount")
    assert amount_field.type == "numeric_like"
    assert any(row.get("amount") == "1.234,56" for row in result.sample)


def test_us2_4_unknown_identifier_raises_not_found() -> None:
    dataset = Dataset(FIXTURES)
    with pytest.raises(DataSourceNotFoundError):
        inspect_schema(dataset, "does-not-exist.csv")


def test_us2_5_unreadable_source_raises() -> None:
    dataset = Dataset(FIXTURES)
    with pytest.raises(UnreadableSourceError):
        inspect_schema(dataset, "broken.csv")
