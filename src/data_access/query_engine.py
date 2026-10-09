"""QueryEngine protocol + its pandas-backed implementation (research.md §6).

Field-existence and numeric-type validation (which need the identifier for error
messages) live in capabilities.py, not here — this module assumes its inputs are
already valid and does purely mechanical work over an in-memory DataFrame of raw
string values.

`equals`/`contains` follow the `MatchRules` the engine is built with
(data_access.text_matching; specs/009-text-value-matching/contracts/text-matching.md).

`aggregate` receives the **unfiltered** source frame and runs the whole query itself:
filter → group → aggregate → order (007 research.md §1). Numeric-like classification
of fields, the group limit and the group counts stay in the capability, because
classification must look at the unfiltered source and the limit mirrors `query_rows`.
"""

from typing import Protocol, cast

import pandas as pd

from data_access.models import (
    AggregationGroup,
    AggregationRequest,
    ContainsCondition,
    EqualsCondition,
    FilterCondition,
    RangeCondition,
)
from data_access.numeric import parse_locale_number
from data_access.text_matching import MatchRules, TextMatchingConfig

_NUMERIC_FUNCTIONS = ("sum", "mean", "min", "max")


class QueryEngine(Protocol):
    def query_rows(self, df: pd.DataFrame, filters: list[FilterCondition]) -> pd.DataFrame: ...
    def aggregate(
        self,
        df: pd.DataFrame,
        request: AggregationRequest,
        numeric_group_fields: frozenset[str],
    ) -> list[AggregationGroup]: ...


class PandasQueryEngine:
    """The pandas `QueryEngine`.

    `rules` are the text-matching rules `equals`/`contains` filters apply (009
    contracts/text-matching.md). They are a constructor argument, not part of the
    `QueryEngine` protocol, so another engine receives the same `MatchRules` the same
    way. The default is the rules of the default `TextMatchingConfig`.
    """

    def __init__(self, rules: MatchRules | None = None) -> None:
        self._rules = rules if rules is not None else MatchRules.from_config(TextMatchingConfig())

    def query_rows(self, df: pd.DataFrame, filters: list[FilterCondition]) -> pd.DataFrame:
        mask = pd.Series(True, index=df.index)
        for condition in filters:
            mask &= self._condition_mask(df, condition)
        return cast(pd.DataFrame, df[mask])

    def aggregate(
        self,
        df: pd.DataFrame,
        request: AggregationRequest,
        numeric_group_fields: frozenset[str],
    ) -> list[AggregationGroup]:
        """Filter → group → aggregate → order, returning every group (no limit).

        `df` is the unfiltered source; `request.filters` are applied here with the same
        mask as `query_rows`. `numeric_group_fields` names the `group_by` fields the
        capability classified as numeric-like, which are ordered as numbers rather than
        as text (research.md §7).
        """
        filtered = self.query_rows(df, request.filters)
        if filtered.empty:
            return []

        # Parse each numeric value field once per request, not once per group (§5).
        parsed: dict[str, pd.Series] = {
            spec.value_field: cast(pd.Series, filtered[spec.value_field].map(_parse_number))
            for spec in request.aggregates
            if spec.function in _NUMERIC_FUNCTIONS
        }

        groups: list[AggregationGroup] = []
        grouped = filtered.groupby(request.group_by, dropna=False, sort=False)
        for key, group_df in grouped:
            key_tuple = key if isinstance(key, tuple) else (key,)
            group_values = {
                field: (None if bool(pd.isna(value)) else str(value))
                for field, value in zip(request.group_by, key_tuple)
            }
            results: dict[str, float | int | None] = {}
            for spec in request.aggregates:
                result_key = f"{spec.function}_{spec.value_field}"
                if spec.function == "count":
                    results[result_key] = int(len(group_df))
                elif spec.function == "count_distinct":
                    raw_values = group_df[spec.value_field].tolist()
                    results[result_key] = len({v for v in raw_values if not _is_missing(v)})
                else:
                    numbers = [
                        float(v) for v in parsed[spec.value_field].loc[group_df.index].dropna()
                    ]
                    results[result_key] = _numeric_result(spec.function, numbers)
            groups.append(AggregationGroup(group_values=group_values, results=results))

        return _order_groups(groups, request, numeric_group_fields)

    def _condition_mask(self, df: pd.DataFrame, condition: FilterCondition) -> pd.Series:
        """The rows one condition keeps.

        `equals`/`contains` use `self._rules` (009 contracts/text-matching.md): `equals`
        compares whole normalized values (case, accents and punctuation ignored);
        `contains` needs every non-stopword query word to start a word of the stored
        value, in any order. Each distinct stored value is judged once and mapped back
        onto the column (research.md R2). Missing values (`_is_missing`) never match
        either operator, so since 009 `equals ""` and `contains ""` skip empty cells.
        `range` is unchanged.
        """
        column = df[condition.field]

        if isinstance(condition, (EqualsCondition, ContainsCondition)):
            if isinstance(condition, EqualsCondition):
                match = self._rules.equals
            else:
                match = self._rules.contains
            value = condition.value
            judged = {
                stored: match(str(stored), value)
                for stored in column.unique()
                if not _is_missing(stored)
            }
            return cast(pd.Series, column.map(lambda stored: judged.get(stored, False)).astype(bool))

        if isinstance(condition, RangeCondition):
            numeric = column.map(lambda v: None if v is None else parse_locale_number(v))
            mask = pd.Series(True, index=df.index)
            if condition.min is not None:
                lo = condition.min
                mask &= numeric.map(lambda v: v is not None and v >= lo)
            if condition.max is not None:
                hi = condition.max
                mask &= numeric.map(lambda v: v is not None and v <= hi)
            return mask

        raise AssertionError(f"Unhandled filter condition: {condition!r}")


def _is_missing(value: object) -> bool:
    """Missing = None/NaN, or a string that is empty after strip() (research.md §4)."""
    if isinstance(value, str):
        return not value.strip()
    return value is None or bool(pd.isna(value))


def _parse_number(value: object) -> float | None:
    return None if _is_missing(value) else parse_locale_number(str(value))


def _numeric_result(function: str, numbers: list[float]) -> float | None:
    if function == "sum":
        return float(sum(numbers))
    if not numbers:
        return None
    if function == "mean":
        return sum(numbers) / len(numbers)
    if function == "min":
        return min(numbers)
    if function == "max":
        return max(numbers)
    raise AssertionError(f"Unhandled aggregate function: {function!r}")


def _group_sort_value(raw: str | None, numeric: bool) -> float | str | None:
    """The comparable value of a grouping field, or None when missing/unparseable."""
    if raw is None or _is_missing(raw):
        return None
    return parse_locale_number(raw) if numeric else raw


def _order_groups(
    groups: list[AggregationGroup],
    request: AggregationRequest,
    numeric_group_fields: frozenset[str],
) -> list[AggregationGroup]:
    """Stable multi-pass ordering (research.md §7).

    Base pass: ascending by every grouping field, missing last, raw text as the final
    tie-breaker, so the order never depends on source row order. Then one pass per
    `order_by` key, last key first; each pass puts missing values after present ones
    regardless of direction, and stability keeps earlier passes as tie-breakers.
    """

    def group_value(group: AggregationGroup, field: str) -> float | str | None:
        return _group_sort_value(group.group_values[field], field in numeric_group_fields)

    def base_key(group: AggregationGroup) -> tuple[object, ...]:
        by_field = []
        for field in request.group_by:
            value = group_value(group, field)
            by_field.append((1, 0) if value is None else (0, value))
        raw = tuple((v is None, v or "") for v in group.group_values.values())
        return (*by_field, raw)

    ordered = sorted(groups, key=base_key)

    for sort_key in reversed(request.order_by):
        if sort_key.key in request.group_by:
            field = sort_key.key
            values = [group_value(g, field) for g in ordered]
        else:
            values = [g.results[sort_key.key] for g in ordered]
        present = [(v, g) for v, g in zip(values, ordered) if v is not None]
        missing = [g for v, g in zip(values, ordered) if v is None]
        present.sort(
            key=lambda pair: cast(float | str, pair[0]), reverse=sort_key.direction == "desc"
        )
        ordered = [g for _, g in present] + missing

    return ordered
