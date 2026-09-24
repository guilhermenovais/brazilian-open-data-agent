"""Contract tests for aggregation.

- `001` US4.1-US4.8 (`specs/001-data-access-tools/contracts/aggregation.md`).
- `007` US1-US3 and edge cases (`specs/007-aggregate-rows-enhancements/contracts/aggregation.md`).
  Expected values are hand-computed from the `transfers.csv` fixture table in
  `specs/007-aggregate-rows-enhancements/tasks.md`.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from data_access.capabilities import aggregate_rows, query_rows
from data_access.dataset import Dataset
from data_access.exceptions import (
    DataSourceNotFoundError,
    FieldNotFoundError,
    InvalidSortKeyError,
    NumericTypeError,
    UnreadableSourceError,
)
from data_access.models import (
    AggregateSpec,
    AggregationGroup,
    AggregationRequest,
    AggregationResult,
    EqualsCondition,
    FilterCondition,
    RangeCondition,
    SortKey,
)

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "data_access" / "sample_dataset"
FIXTURE_ID = "transfers.csv"


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
    assert result.total_group_count == 0
    assert result.truncated is False


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


# --- 007: shared helpers ----------------------------------------------------------

_YEAR_2023: list[FilterCondition] = [EqualsCondition(field="ano", value="2023")]


def _by_group(result: AggregationResult, key: str) -> dict[str | None, float | int | None]:
    """Maps a single-field group value to `results[key]`."""
    return {next(iter(g.group_values.values())): g.results[key] for g in result.groups}


def _group_tuple(group: AggregationGroup) -> tuple[str | None, ...]:
    return tuple(group.group_values.values())


def _aggregate(
    group_by: list[str],
    aggregates: list[tuple[str, str]],
    *,
    filters: list[FilterCondition] | None = None,
    order_by: list[SortKey] | None = None,
    limit: int | None = None,
    dataset: Dataset | None = None,
    identifier: str = FIXTURE_ID,
) -> AggregationResult:
    request = AggregationRequest(
        group_by=group_by,
        aggregates=[
            AggregateSpec(value_field=field, function=function)  # type: ignore[arg-type]
            for function, field in aggregates
        ],
        filters=filters or [],
        order_by=order_by or [],
        limit=limit,
    )
    return aggregate_rows(dataset or Dataset(FIXTURES), identifier, request)


def test_007_result_reports_total_group_count_and_not_truncated_without_limit() -> None:
    result = _aggregate(["orgao"], [("count", "ano")])
    assert result.total_group_count == 3
    assert result.truncated is False
    assert len(result.groups) == 3


# --- 007 US1: filters ------------------------------------------------------------


def test_007_us1_1_filter_restricts_sum_to_matching_rows() -> None:
    result = _aggregate(["orgao"], [("sum", "valor")], filters=_YEAR_2023)
    sums = _by_group(result, "sum_valor")
    assert sums == {
        "MS": pytest.approx(60.0),
        "ME": pytest.approx(3234.56),
        "MC": pytest.approx(5.0),
    }


def test_007_us1_6_no_filters_matches_unfiltered_behavior() -> None:
    result = _aggregate(["orgao"], [("sum", "valor")])
    sums = _by_group(result, "sum_valor")
    assert sums == {
        "MS": pytest.approx(1560.0),
        "ME": pytest.approx(5234.56),
        "MC": pytest.approx(104.9),
    }


def test_007_us1_2_multiple_filters_combined_with_and() -> None:
    year_and_sp: list[FilterCondition] = [*_YEAR_2023, EqualsCondition(field="uf", value="SP")]
    result = _aggregate(["orgao"], [("sum", "valor")], filters=year_and_sp)
    assert _by_group(result, "sum_valor") == {
        "MS": pytest.approx(30.0),
        "ME": pytest.approx(1234.56),
        "MC": pytest.approx(0.0),
    }

    year_and_min: list[FilterCondition] = [*_YEAR_2023, RangeCondition(field="valor", min=15)]
    result = _aggregate(["orgao"], [("sum", "valor"), ("count", "ano")], filters=year_and_min)
    assert _by_group(result, "sum_valor") == {
        "MS": pytest.approx(50.0),
        "ME": pytest.approx(3234.56),
    }

    # The rows the aggregation grouped are exactly the rows query_rows matches (FR-001).
    rows = query_rows(Dataset(FIXTURES), FIXTURE_ID, year_and_min)
    grouped_row_count = sum(g.results["count_ano"] or 0 for g in result.groups)
    assert grouped_row_count == rows.total_match_count == 4


def test_007_us1_3_filters_matching_nothing_return_zero_groups() -> None:
    result = _aggregate(
        ["orgao"], [("sum", "valor")], filters=[EqualsCondition(field="ano", value="1999")]
    )
    assert result.groups == []
    assert result.total_group_count == 0
    assert result.truncated is False


def test_007_us1_4_unknown_filter_field_raises_field_not_found() -> None:
    with pytest.raises(FieldNotFoundError) as exc_info:
        _aggregate(
            ["orgao"], [("count", "ano")], filters=[EqualsCondition(field="nope", value="x")]
        )
    assert exc_info.value.field == "nope"


def test_007_us1_5_range_filter_on_text_field_raises_numeric_type_error() -> None:
    with pytest.raises(NumericTypeError) as exc_info:
        _aggregate(
            ["orgao"], [("count", "ano")], filters=[RangeCondition(field="fornecedor", min=1)]
        )
    assert exc_info.value.field == "fornecedor"


def test_007_us1_5_range_filter_validated_even_on_empty_source(tmp_path: Path) -> None:
    (tmp_path / "empty.csv").write_text("a,b\n")
    with pytest.raises(NumericTypeError) as exc_info:
        _aggregate(
            ["a"], [("count", "b")],
            filters=[RangeCondition(field="b", min=1)],
            dataset=Dataset(tmp_path), identifier="empty.csv",
        )
    assert exc_info.value.field == "b"


# --- 007 US2: mean / min / max / count_distinct ----------------------------------

_MEAN_MIN_MAX = [("mean", "valor"), ("min", "valor"), ("max", "valor")]


def test_007_us2_1_mean_min_max_of_simple_values() -> None:
    result = _aggregate(["orgao"], _MEAN_MIN_MAX, filters=_YEAR_2023)
    assert _by_group(result, "mean_valor")["MS"] == pytest.approx(20.0)
    assert _by_group(result, "min_valor")["MS"] == pytest.approx(10.0)
    assert _by_group(result, "max_valor")["MS"] == pytest.approx(30.0)


def test_007_us2_2_brazilian_formatted_values_parsed_like_sum() -> None:
    result = _aggregate(["orgao"], _MEAN_MIN_MAX, filters=_YEAR_2023)
    assert _by_group(result, "mean_valor")["ME"] == pytest.approx(1617.28)
    assert _by_group(result, "min_valor")["ME"] == pytest.approx(1234.56)
    assert _by_group(result, "max_valor")["ME"] == pytest.approx(2000.0)


def test_007_us2_3_missing_values_ignored_not_zero() -> None:
    result = _aggregate(["orgao"], _MEAN_MIN_MAX, filters=_YEAR_2023)
    assert _by_group(result, "mean_valor")["MC"] == pytest.approx(5.0)
    assert _by_group(result, "min_valor")["MC"] == pytest.approx(5.0)
    assert _by_group(result, "max_valor")["MC"] == pytest.approx(5.0)


def test_007_us2_4_all_missing_group_reports_none() -> None:
    result = _aggregate(
        ["orgao", "uf"], [*_MEAN_MIN_MAX, ("sum", "valor")], filters=_YEAR_2023
    )
    (mc_sp,) = [g for g in result.groups if g.group_values == {"orgao": "MC", "uf": "SP"}]
    assert mc_sp.results["mean_valor"] is None
    assert mc_sp.results["min_valor"] is None
    assert mc_sp.results["max_valor"] is None
    assert mc_sp.results["sum_valor"] == 0.0


@pytest.mark.parametrize("function", ["mean", "min", "max"])
def test_007_us2_5_mean_min_max_on_text_field_raise_numeric_type_error(function: str) -> None:
    with pytest.raises(NumericTypeError) as exc_info:
        _aggregate(["orgao"], [(function, "fornecedor")])
    assert exc_info.value.field == "fornecedor"


def test_007_us2_5_numeric_check_uses_whole_source_even_when_filters_match_nothing() -> None:
    with pytest.raises(NumericTypeError):
        _aggregate(
            ["orgao"], [("mean", "fornecedor")],
            filters=[EqualsCondition(field="ano", value="1999")],
        )


def test_007_us2_6_count_distinct_excludes_missing() -> None:
    result = _aggregate(["uf"], [("count_distinct", "fornecedor")], filters=_YEAR_2023)
    assert _by_group(result, "count_distinct_fornecedor")["SP"] == 2


def test_007_us2_7_count_distinct_accepted_on_numeric_and_text_fields() -> None:
    result = _aggregate(
        ["orgao"], [("count_distinct", "mes"), ("count_distinct", "fornecedor")]
    )
    by_mes = _by_group(result, "count_distinct_mes")
    by_fornecedor = _by_group(result, "count_distinct_fornecedor")
    assert by_mes == {"MS": 3, "ME": 3, "MC": 1}
    assert by_fornecedor == {"MS": 2, "ME": 2, "MC": 2}
    assert all(type(v) is int for v in [*by_mes.values(), *by_fornecedor.values()])


@pytest.mark.parametrize("function", ["count", "sum", "mean", "min", "max", "count_distinct"])
def test_007_edge_empty_source_returns_zero_groups_for_every_function(
    tmp_path: Path, function: str
) -> None:
    (tmp_path / "empty.csv").write_text("g,v\n")
    result = _aggregate(
        ["g"], [(function, "v")], dataset=Dataset(tmp_path), identifier="empty.csv"
    )
    assert result.groups == []
    assert result.total_group_count == 0


def test_007_edge_duplicate_spec_produces_single_key() -> None:
    result = _aggregate(["orgao"], [("mean", "valor"), ("mean", "valor")])
    assert all(list(g.results) == ["mean_valor"] for g in result.groups)


def test_007_edge_unparseable_values_skipped() -> None:
    result = _aggregate(["orgao"], [("max", "valor")], filters=_YEAR_2023)
    assert _by_group(result, "max_valor")["ME"] == pytest.approx(2000.0)


# --- 007 US3: order_by / limit ---------------------------------------------------


def test_007_us3_1_order_desc_with_limit_returns_top_n(tmp_path: Path) -> None:
    lines = ["municipio,valor"] + [f'M{i:02d},"{i}.000,00"' for i in range(1, 51)]
    (tmp_path / "municipios.csv").write_text("\n".join(lines) + "\n")
    result = _aggregate(
        ["municipio"], [("sum", "valor")],
        order_by=[SortKey(key="sum_valor", direction="desc")], limit=5,
        dataset=Dataset(tmp_path), identifier="municipios.csv",
    )
    assert [g.group_values["municipio"] for g in result.groups] == [
        "M50", "M49", "M48", "M47", "M46",
    ]
    assert [g.results["sum_valor"] for g in result.groups] == [
        50000.0, 49000.0, 48000.0, 47000.0, 46000.0,
    ]
    assert result.total_group_count == 50
    assert result.truncated is True


def test_007_us3_2_order_by_text_grouping_field_ascending() -> None:
    result = _aggregate(["uf"], [("count", "ano")], order_by=[SortKey(key="uf")])
    assert [g.group_values["uf"] for g in result.groups] == ["MG", "RJ", "SP"]


def test_007_us3_2_order_by_numeric_like_grouping_field_numerically() -> None:
    result = _aggregate(["mes"], [("count", "ano")], order_by=[SortKey(key="mes")])
    assert [g.group_values["mes"] for g in result.groups] == ["1", "2", "10", "12", ""]


def test_007_us3_3_multiple_sort_keys_break_ties() -> None:
    result = _aggregate(
        ["orgao", "uf"], [("count", "ano")],
        order_by=[SortKey(key="count_ano", direction="desc"), SortKey(key="orgao")],
    )
    assert [_group_tuple(g) for g in result.groups] == [
        ("MS", "SP"), ("ME", "MG"), ("ME", "SP"), ("MS", "RJ"),
        ("MC", "MG"), ("MC", "RJ"), ("MC", "SP"),
    ]


def test_007_us3_4_missing_sort_values_last_in_both_directions() -> None:
    asc = _aggregate(
        ["orgao", "uf"], [("mean", "valor")], filters=_YEAR_2023,
        order_by=[SortKey(key="mean_valor")],
    )
    assert [_group_tuple(g) for g in asc.groups] == [
        ("MC", "MG"), ("MS", "SP"), ("MS", "RJ"), ("ME", "SP"), ("ME", "MG"), ("MC", "SP"),
    ]
    desc = _aggregate(
        ["orgao", "uf"], [("mean", "valor")], filters=_YEAR_2023,
        order_by=[SortKey(key="mean_valor", direction="desc")],
    )
    assert [_group_tuple(g) for g in desc.groups] == [
        ("ME", "MG"), ("ME", "SP"), ("MS", "RJ"), ("MS", "SP"), ("MC", "MG"), ("MC", "SP"),
    ]
    by_mes = _aggregate(
        ["mes"], [("count", "ano")], order_by=[SortKey(key="mes", direction="desc")]
    )
    assert [g.group_values["mes"] for g in by_mes.groups] == ["12", "10", "2", "1", ""]


def test_007_us3_5_limit_reports_total_and_truncated() -> None:
    result = _aggregate(["orgao", "uf"], [("count", "ano")], limit=3)
    assert len(result.groups) == 3
    assert result.total_group_count == 7
    assert result.truncated is True


def test_007_us3_6_limit_without_order_uses_default_order() -> None:
    result = _aggregate(["uf"], [("count", "ano")], limit=2)
    assert [g.group_values["uf"] for g in result.groups] == ["MG", "RJ"]
    assert result.total_group_count == 3
    assert result.truncated is True


def test_007_edge_limit_larger_than_group_count_not_truncated() -> None:
    result = _aggregate(["uf"], [("count", "ano")], limit=10)
    assert len(result.groups) == 3
    assert result.total_group_count == 3
    assert result.truncated is False


def test_007_us1_filters_plus_limit_limit_counts_groups() -> None:
    result = _aggregate(
        ["orgao"], [("sum", "valor")], filters=_YEAR_2023,
        order_by=[SortKey(key="sum_valor", direction="desc")], limit=1,
    )
    assert _by_group(result, "sum_valor") == {"ME": pytest.approx(3234.56)}
    assert result.total_group_count == 3
    assert result.truncated is True


def test_007_us3_7_invalid_sort_key_names_key_and_lists_valid_keys() -> None:
    with pytest.raises(InvalidSortKeyError) as exc_info:
        _aggregate(["orgao"], [("sum", "valor")], order_by=[SortKey(key="nope")])
    assert exc_info.value.key == "nope"
    assert exc_info.value.valid_keys == ["orgao", "sum_valor"]
    assert "'nope'" in str(exc_info.value)
    assert "['orgao', 'sum_valor']" in str(exc_info.value)


def test_007_us3_7_invalid_sort_key_raised_even_on_empty_source(tmp_path: Path) -> None:
    (tmp_path / "empty.csv").write_text("g,v\n")
    with pytest.raises(InvalidSortKeyError):
        _aggregate(
            ["g"], [("count", "v")], order_by=[SortKey(key="nope")],
            dataset=Dataset(tmp_path), identifier="empty.csv",
        )


@pytest.mark.parametrize("limit", [0, -1])
def test_007_us3_8_zero_or_negative_limit_rejected(limit: int) -> None:
    with pytest.raises(ValidationError):
        AggregationRequest(
            group_by=["orgao"],
            aggregates=[AggregateSpec(value_field="ano", function="count")],
            limit=limit,
        )


def test_007_sort_key_matching_both_group_field_and_result_key_refers_to_group_field(
    tmp_path: Path,
) -> None:
    # The source has a column literally named `sum_valor`, so "sum_valor" is both a
    # grouping field and the result key of sum(valor). Ordering by the grouping field
    # (text, desc) gives c, b, a; ordering by the sum would give a, c, b.
    (tmp_path / "clash.csv").write_text("sum_valor,valor\nb,1\na,5\nc,3\n")
    result = _aggregate(
        ["sum_valor"], [("sum", "valor")],
        order_by=[SortKey(key="sum_valor", direction="desc")],
        dataset=Dataset(tmp_path), identifier="clash.csv",
    )
    assert [g.group_values["sum_valor"] for g in result.groups] == ["c", "b", "a"]
