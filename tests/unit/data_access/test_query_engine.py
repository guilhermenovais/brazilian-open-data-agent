"""Unit tests for `PandasQueryEngine.aggregate` group ordering (research.md §7).

Each test name states one ordering rule. Frames hold raw string values, as the
dataset reader produces them.
"""

import pandas as pd

from data_access.models import AggregateSpec, AggregationGroup, AggregationRequest, SortKey
from data_access.query_engine import PandasQueryEngine


def _aggregate(
    rows: dict[str, list[str | None]],
    group_by: list[str],
    *,
    aggregates: list[AggregateSpec] | None = None,
    order_by: list[SortKey] | None = None,
    numeric_group_fields: frozenset[str] = frozenset(),
    limit: int | None = None,
    df: pd.DataFrame | None = None,
) -> list[AggregationGroup]:
    request = AggregationRequest(
        group_by=group_by,
        aggregates=aggregates or [AggregateSpec(value_field=group_by[0], function="count")],
        order_by=order_by or [],
        limit=limit,
    )
    frame = df if df is not None else pd.DataFrame(rows, dtype=object)
    return PandasQueryEngine().aggregate(frame, request, numeric_group_fields)


def _values(groups: list[AggregationGroup], field: str) -> list[str | None]:
    return [g.group_values[field] for g in groups]


def test_default_order_ascending_by_group_values_missing_last() -> None:
    groups = _aggregate({"g": ["b", "", "a", None, "b"]}, ["g"])
    assert _values(groups, "g") == ["a", "b", "", None]


def test_default_order_independent_of_source_row_order() -> None:
    rows: dict[str, list[str | None]] = {
        "g": ["x", "y", "z", "x", "", "w", "y"],
        "h": ["2", "1", "10", "1", "3", "", "2"],
    }
    df = pd.DataFrame(rows, dtype=object)
    expected = _aggregate(rows, ["g", "h"], numeric_group_fields=frozenset({"h"}))
    for seed in range(5):
        shuffled = df.sample(frac=1, random_state=seed)
        assert (
            _aggregate({}, ["g", "h"], numeric_group_fields=frozenset({"h"}), df=shuffled)
            == expected
        )


def test_numeric_group_field_sorted_numerically() -> None:
    groups = _aggregate({"m": ["12", "2", "10", "1"]}, ["m"], numeric_group_fields=frozenset({"m"}))
    assert _values(groups, "m") == ["1", "2", "10", "12"]


def test_numeric_group_field_unparseable_value_treated_as_missing_and_last() -> None:
    groups = _aggregate({"m": ["10", "x", "2"]}, ["m"], numeric_group_fields=frozenset({"m"}))
    assert _values(groups, "m") == ["2", "10", "x"]


def test_numeric_equal_group_values_tie_broken_by_raw_text() -> None:
    groups = _aggregate({"m": ["1,0", "1"]}, ["m"], numeric_group_fields=frozenset({"m"}))
    assert _values(groups, "m") == ["1", "1,0"]


def test_text_group_field_sorted_by_code_point() -> None:
    groups = _aggregate({"uf": ["São Paulo", "acre", "Sergipe", "Bahia"]}, ["uf"])
    assert _values(groups, "uf") == ["Bahia", "Sergipe", "São Paulo", "acre"]


_MEAN_V = [AggregateSpec(value_field="v", function="mean")]
_MEAN_ROWS: dict[str, list[str | None]] = {
    "g": ["a", "b", "c", "d"],
    "v": ["3", "", "1", "2"],
}


def test_result_key_missing_values_last_ascending() -> None:
    groups = _aggregate(_MEAN_ROWS, ["g"], aggregates=_MEAN_V, order_by=[SortKey(key="mean_v")])
    assert _values(groups, "g") == ["c", "d", "a", "b"]


def test_result_key_missing_values_last_descending() -> None:
    groups = _aggregate(
        _MEAN_ROWS, ["g"], aggregates=_MEAN_V,
        order_by=[SortKey(key="mean_v", direction="desc")],
    )
    assert _values(groups, "g") == ["a", "d", "c", "b"]


def test_later_sort_keys_break_ties_of_earlier_keys() -> None:
    groups = _aggregate(
        {"g": ["a", "b", "b", "c", "c", "d"]}, ["g"],
        aggregates=[AggregateSpec(value_field="g", function="count")],
        order_by=[SortKey(key="count_g", direction="desc"), SortKey(key="g", direction="desc")],
    )
    assert _values(groups, "g") == ["c", "b", "d", "a"]


def test_ties_after_all_sort_keys_fall_back_to_default_order() -> None:
    groups = _aggregate(
        {"g": ["c", "a", "d", "b"]}, ["g"],
        aggregates=[AggregateSpec(value_field="g", function="count")],
        order_by=[SortKey(key="count_g", direction="desc")],
    )
    assert _values(groups, "g") == ["a", "b", "c", "d"]


def test_engine_returns_all_groups_no_limit_applied() -> None:
    groups = _aggregate({"g": ["a", "b", "c"]}, ["g"], limit=1)
    assert len(groups) == 3
