"""Contract tests for filtered row query, US3.1-US3.9 (contracts/query.md)."""

from pathlib import Path

import pytest

from data_access.capabilities import ROW_QUERY_CAP, query_rows
from data_access.dataset import Dataset
from data_access.exceptions import (
    DataSourceNotFoundError,
    FieldNotFoundError,
    NumericTypeError,
    UnreadableSourceError,
)
from data_access.models import ContainsCondition, EqualsCondition, RangeCondition

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "data_access" / "sample_dataset"


def test_us3_1_equals_condition_only_exact_matches() -> None:
    dataset = Dataset(FIXTURES)
    result = query_rows(
        dataset, "orders/2024/sales.csv",
        filters=[EqualsCondition(field="region", value="North")],
    )
    assert result.rows
    assert all(row["region"] == "North" for row in result.rows)


def test_us3_2_contains_condition_case_insensitive_substring() -> None:
    dataset = Dataset(FIXTURES)
    result = query_rows(
        dataset, "customers.csv",
        filters=[ContainsCondition(field="name", value="AL")],
    )
    names = {row["name"] for row in result.rows}
    assert names == {"Alice"}


def test_us3_3_range_condition_matches_true_numeric_value_not_lexical() -> None:
    dataset = Dataset(FIXTURES)
    result = query_rows(
        dataset, "orders/2024/sales.csv",
        filters=[RangeCondition(field="amount", min=1000, max=2000)],
    )
    matched_ids = {row["id"] for row in result.rows}
    # amount values: 1.234,56 (BR->1234.56), 1,234.56 (US->1234.56), 2.500,00 (2500),
    # 750.25, 3.100,75 (3100.75), 1,999.99 (1999.99)
    assert matched_ids == {"1", "2", "6"}


def test_us3_4_multiple_conditions_and_semantics() -> None:
    dataset = Dataset(FIXTURES)
    result = query_rows(
        dataset, "orders/2024/sales.csv",
        filters=[
            EqualsCondition(field="region", value="North"),
            RangeCondition(field="amount", min=1000, max=2000),
        ],
    )
    assert {row["id"] for row in result.rows} == {"1"}


def test_us3_5_more_matches_than_cap_truncated_with_true_total(tmp_path: Path) -> None:
    lines = ["id,value"] + [f"{i},x" for i in range(ROW_QUERY_CAP + 25)]
    (tmp_path / "big.csv").write_text("\n".join(lines) + "\n")
    dataset = Dataset(tmp_path)

    result = query_rows(dataset, "big.csv", filters=[])

    assert result.returned_count == ROW_QUERY_CAP
    assert result.total_match_count == ROW_QUERY_CAP + 25
    assert result.truncated is True


def test_us3_6_filter_on_nonexistent_field_raises() -> None:
    dataset = Dataset(FIXTURES)
    with pytest.raises(FieldNotFoundError):
        query_rows(
            dataset, "customers.csv",
            filters=[EqualsCondition(field="does_not_exist", value="x")],
        )


def test_us3_datasource_not_found_raises() -> None:
    dataset = Dataset(FIXTURES)
    with pytest.raises(DataSourceNotFoundError):
        query_rows(dataset, "does-not-exist.csv", filters=[])


def test_us3_unreadable_source_raises() -> None:
    dataset = Dataset(FIXTURES)
    with pytest.raises(UnreadableSourceError):
        query_rows(dataset, "broken.csv", filters=[])


def test_us3_range_on_non_numeric_like_field_raises() -> None:
    dataset = Dataset(FIXTURES)
    with pytest.raises(NumericTypeError):
        query_rows(
            dataset, "customers.csv",
            filters=[RangeCondition(field="name", min=0, max=100)],
        )
