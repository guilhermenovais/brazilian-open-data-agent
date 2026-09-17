"""The four public capability entry points of the data access tool layer.

Plain Python functions (Constitution Engineering Principle 1 — no `pydantic-ai`
import). A future `@agent.tool` adapter wraps each of these 1:1.
"""

import pandas as pd

from data_access.dataset import Dataset
from data_access.exceptions import FieldNotFoundError, NumericTypeError
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
            type="numeric_like" if is_numeric_like(sample_df[col].tolist()) else "text",
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
    df = dataset.read(identifier)

    for field in request.group_by:
        if field not in df.columns:
            raise FieldNotFoundError(identifier, field)
    for spec in request.aggregates:
        if spec.value_field not in df.columns:
            raise FieldNotFoundError(identifier, spec.value_field)

    if df.empty:
        return AggregationResult(identifier=identifier, groups=[])

    for spec in request.aggregates:
        if spec.function == "sum":
            sample_values = df[spec.value_field].head(SAMPLE_SIZE_CAP).tolist()
            if not is_numeric_like(sample_values):
                raise NumericTypeError(identifier, spec.value_field)

    groups = _ENGINE.aggregate(df, request)
    return AggregationResult(identifier=identifier, groups=groups)


def _validate_filter_fields(
    identifier: str, df: pd.DataFrame, filters: list[FilterCondition]
) -> None:
    for condition in filters:
        if condition.field not in df.columns:
            raise FieldNotFoundError(identifier, condition.field)
        if isinstance(condition, RangeCondition):
            sample_values = df[condition.field].head(SAMPLE_SIZE_CAP).tolist()
            if not is_numeric_like(sample_values):
                raise NumericTypeError(identifier, condition.field)
