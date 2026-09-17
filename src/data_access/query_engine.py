"""QueryEngine protocol + its pandas-backed implementation (research.md §6).

Field-existence and numeric-type validation (which need the identifier for error
messages) live in capabilities.py, not here — this module assumes its inputs are
already valid and does purely mechanical filtering/aggregation over an in-memory
DataFrame of raw string values.
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


class QueryEngine(Protocol):
    def query_rows(self, df: pd.DataFrame, filters: list[FilterCondition]) -> pd.DataFrame: ...
    def aggregate(self, df: pd.DataFrame, request: AggregationRequest) -> list[AggregationGroup]: ...


class PandasQueryEngine:
    def query_rows(self, df: pd.DataFrame, filters: list[FilterCondition]) -> pd.DataFrame:
        mask = pd.Series(True, index=df.index)
        for condition in filters:
            mask &= self._condition_mask(df, condition)
        return cast(pd.DataFrame, df[mask])

    def aggregate(self, df: pd.DataFrame, request: AggregationRequest) -> list[AggregationGroup]:
        if df.empty:
            return []

        groups: list[AggregationGroup] = []
        grouped = df.groupby(request.group_by, dropna=False, sort=False)
        for key, group_df in grouped:
            key_tuple = key if isinstance(key, tuple) else (key,)
            group_values = {
                field: (None if bool(pd.isna(value)) else str(value))
                for field, value in zip(request.group_by, key_tuple)
            }
            results: dict[str, float | int] = {}
            for spec in request.aggregates:
                result_key = f"{spec.function}_{spec.value_field}"
                if spec.function == "count":
                    results[result_key] = int(len(group_df))
                else:
                    numeric = cast(
                        pd.Series,
                        group_df[spec.value_field].map(
                            lambda v: None if v is None else parse_locale_number(v)
                        ),
                    )
                    total: float = numeric.dropna().sum()
                    results[result_key] = float(total)
            groups.append(AggregationGroup(group_values=group_values, results=results))
        return groups

    def _condition_mask(self, df: pd.DataFrame, condition: FilterCondition) -> pd.Series:
        column = df[condition.field]

        if isinstance(condition, EqualsCondition):
            return column == condition.value

        if isinstance(condition, ContainsCondition):
            needle = condition.value.lower()
            return column.fillna("").str.lower().str.contains(needle, regex=False)

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
