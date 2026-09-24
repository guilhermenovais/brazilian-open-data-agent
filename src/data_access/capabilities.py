"""The four public capability entry points of the data access tool layer.

Plain Python functions (Constitution Engineering Principle 1 — no `pydantic-ai`
import). A future `@agent.tool` adapter wraps each of these 1:1.

Split with the query engine: capabilities read the source, validate requests (errors
carry the identifier), classify fields as numeric-like on the **unfiltered** source,
and apply result caps and counts. The engine does the mechanical work — filtering,
and for aggregation filter → group → aggregate → order.
"""

import pandas as pd

from data_access.dataset import Dataset
from data_access.exceptions import FieldNotFoundError, InvalidSortKeyError, NumericTypeError
from data_access.models import (
    AggregationRequest,
    AggregationResult,
    DiscoveryResult,
    FieldInfo,
    FilterCondition,
    RangeCondition,
    RowQueryResult,
    SchemaInspectionResult,
)
from data_access.numeric import is_numeric_like
from data_access.query_engine import PandasQueryEngine

SAMPLE_SIZE_CAP = 20
ROW_QUERY_CAP = 100

_ENGINE = PandasQueryEngine()


def discover_data_sources(dataset: Dataset) -> DiscoveryResult:
    return DiscoveryResult(sources=dataset.list_sources())


def inspect_schema(dataset: Dataset, identifier: str) -> SchemaInspectionResult:
    df = dataset.read(identifier)
    sample_df = df.head(SAMPLE_SIZE_CAP)

    observed_columns = [col for col in df.columns if bool(sample_df[col].notna().any())]
    fields = [
        FieldInfo(
            name=col,
            type="numeric_like" if _is_numeric_field(df, col) else "text",
        )
        for col in observed_columns
    ]

    sample = [
        {col: row[col] for col in observed_columns}
        for row in sample_df.to_dict(orient="records")
    ]

    return SchemaInspectionResult(identifier=identifier, fields=fields, sample=sample)


def query_rows(
    dataset: Dataset, identifier: str, filters: list[FilterCondition]
) -> RowQueryResult:
    df = dataset.read(identifier)
    _validate_filter_fields(identifier, df, filters)

    matched_df = _ENGINE.query_rows(df, filters)
    total_match_count = len(matched_df)
    rows_df = matched_df.head(ROW_QUERY_CAP)
    rows = rows_df.to_dict(orient="records")
    returned_count = len(rows)

    return RowQueryResult(
        identifier=identifier,
        rows=rows,
        returned_count=returned_count,
        total_match_count=total_match_count,
        truncated=total_match_count > returned_count,
    )


def aggregate_rows(
    dataset: Dataset, identifier: str, request: AggregationRequest
) -> AggregationResult:
    """Group the rows of one source and compute aggregates per group.

    Pipeline: filter → group → aggregate → order (engine) → limit (here).

    Errors, in this order (007 contracts/aggregation.md):
    1. `DataSourceNotFoundError` / `UnreadableSourceError` from reading the source.
    2. `FieldNotFoundError` for an unknown `group_by` field or `value_field`.
    3. `FieldNotFoundError` / `NumericTypeError` for filters, exactly as `query_rows`.
    4. `InvalidSortKeyError` for an `order_by` key that is neither a grouping field
       nor a requested result key.
    Then a source with no rows returns zero groups, and otherwise:
    5. `NumericTypeError` when `sum`/`mean`/`min`/`max` targets a field that is not
       numeric-like on the whole, unfiltered source.
    """
    df = dataset.read(identifier)

    for field in request.group_by:
        if field not in df.columns:
            raise FieldNotFoundError(identifier, field)
    for spec in request.aggregates:
        if spec.value_field not in df.columns:
            raise FieldNotFoundError(identifier, spec.value_field)

    _validate_filter_fields(identifier, df, request.filters)

    valid_keys = list(
        dict.fromkeys(
            [*request.group_by, *(f"{s.function}_{s.value_field}" for s in request.aggregates)]
        )
    )
    for sort_key in request.order_by:
        if sort_key.key not in valid_keys:
            raise InvalidSortKeyError(identifier, sort_key.key, valid_keys)

    if df.empty:
        return AggregationResult(
            identifier=identifier, groups=[], total_group_count=0, truncated=False
        )

    for spec in request.aggregates:
        if spec.function in ("sum", "mean", "min", "max") and not _is_numeric_field(
            df, spec.value_field
        ):
            raise NumericTypeError(identifier, spec.value_field)

    numeric_group_fields = frozenset(f for f in request.group_by if _is_numeric_field(df, f))
    all_groups = _ENGINE.aggregate(df, request, numeric_group_fields)
    total_group_count = len(all_groups)
    groups = all_groups if request.limit is None else all_groups[: request.limit]
    return AggregationResult(
        identifier=identifier,
        groups=groups,
        total_group_count=total_group_count,
        truncated=total_group_count > len(groups),
    )


def _is_numeric_field(df: pd.DataFrame, field: str) -> bool:
    """The one numeric-like rule: `is_numeric_like` over the first SAMPLE_SIZE_CAP
    values of the (unfiltered) source, as `inspect_schema` reports it."""
    return is_numeric_like(df[field].head(SAMPLE_SIZE_CAP).tolist())


def _validate_filter_fields(
    identifier: str, df: pd.DataFrame, filters: list[FilterCondition]
) -> None:
    for condition in filters:
        if condition.field not in df.columns:
            raise FieldNotFoundError(identifier, condition.field)
        if isinstance(condition, RangeCondition) and not _is_numeric_field(df, condition.field):
            raise NumericTypeError(identifier, condition.field)
