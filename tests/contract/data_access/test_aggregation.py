"""Contract tests for aggregation, US4.1-US4.8 (contracts/aggregation.md)."""

from pathlib import Path

import pytest

from data_access.capabilities import aggregate_rows
from data_access.dataset import Dataset
from data_access.exceptions import (
    DataSourceNotFoundError,
    FieldNotFoundError,
    NumericTypeError,
    UnreadableSourceError,
)
from data_access.models import AggregateSpec, AggregationRequest

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "data_access" / "sample_dataset"


def test_us4_1_group_by_categorical_count_matches_true_row_count() -> None:
    dataset = Dataset(FIXTURES)
    result = aggregate_rows(
        dataset, "orders/2024/sales.csv",
        AggregationRequest(
            group_by=["region"],
            aggregates=[AggregateSpec(value_field="id", function="count")],
        ),
    )
    counts = {tuple(g.group_values.values())[0]: g.results["count_id"] for g in result.groups}
    assert counts == {"North": 3, "South": 3}


def test_us4_2_sum_over_brazilian_formatted_field_numerically_correct() -> None:
    dataset = Dataset(FIXTURES)
    result = aggregate_rows(
        dataset, "orders/2024/sales.csv",
        AggregationRequest(
            group_by=["region"],
            aggregates=[AggregateSpec(value_field="amount", function="sum")],
        ),
    )
    sums = {tuple(g.group_values.values())[0]: g.results["sum_amount"] for g in result.groups}
    # North: 1234.56 + 2500.00 + 3100.75 = 6835.31
    # South: 1234.56 + 750.25 + 1999.99 = 3984.80
    assert sums["North"] == pytest.approx(6835.31)
    assert sums["South"] == pytest.approx(3984.80)


def test_us4_3_multiple_group_by_fields_broken_out_by_full_combination() -> None:
    dataset = Dataset(FIXTURES)
    result = aggregate_rows(
        dataset, "orders/2024/sales.csv",
        AggregationRequest(
            group_by=["region", "id"],
            aggregates=[AggregateSpec(value_field="id", function="count")],
        ),
    )
    assert len(result.groups) == 6


def test_us4_4_sum_on_non_numeric_field_raises() -> None:
    dataset = Dataset(FIXTURES)
    with pytest.raises(NumericTypeError):
        aggregate_rows(
            dataset, "orders/2024/sales.csv",
            AggregationRequest(
                group_by=["region"],
                aggregates=[AggregateSpec(value_field="region", function="sum")],
            ),
        )


def test_us4_5_source_with_no_rows_returns_empty_groups(tmp_path: Path) -> None:
    (tmp_path / "empty.csv").write_text("id,region,amount\n")
    dataset = Dataset(tmp_path)
    result = aggregate_rows(
        dataset, "empty.csv",
        AggregationRequest(
            group_by=["region"],
            aggregates=[AggregateSpec(value_field="amount", function="sum")],
        ),
    )
    assert result.groups == []


def test_us4_6_mixed_locale_value_field_each_normalized_per_convention() -> None:
    dataset = Dataset(FIXTURES)
    result = aggregate_rows(
        dataset, "orders/2024/sales.csv",
        AggregationRequest(
            group_by=["region"],
            aggregates=[AggregateSpec(value_field="amount", function="sum")],
        ),
    )
    total = sum(g.results["sum_amount"] for g in result.groups)
    assert total == pytest.approx(6835.31 + 3984.80)


def test_us4_datasource_not_found_raises() -> None:
    dataset = Dataset(FIXTURES)
    with pytest.raises(DataSourceNotFoundError):
        aggregate_rows(
            dataset, "does-not-exist.csv",
            AggregationRequest(
                group_by=["region"],
                aggregates=[AggregateSpec(value_field="amount", function="sum")],
            ),
        )


def test_us4_unreadable_source_raises() -> None:
    dataset = Dataset(FIXTURES)
    with pytest.raises(UnreadableSourceError):
        aggregate_rows(
            dataset, "broken.csv",
            AggregationRequest(
                group_by=["id"],
                aggregates=[AggregateSpec(value_field="id", function="count")],
            ),
        )


def test_us4_unknown_group_by_field_raises() -> None:
    dataset = Dataset(FIXTURES)
    with pytest.raises(FieldNotFoundError):
        aggregate_rows(
            dataset, "orders/2024/sales.csv",
            AggregationRequest(
                group_by=["does_not_exist"],
                aggregates=[AggregateSpec(value_field="amount", function="sum")],
            ),
        )
