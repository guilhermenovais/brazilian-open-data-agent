"""The four public capability entry points of the data access tool layer.

Plain Python functions (Constitution Engineering Principle 1 — no `pydantic-ai`
import). A future `@agent.tool` adapter wraps each of these 1:1.

Split with the query engine: capabilities read the source, validate requests (errors
carry the identifier), classify fields as numeric-like on the **unfiltered** source,
and apply result caps and counts. The engine does the mechanical work — filtering,
and for aggregation filter → group → aggregate → order.

Since 009 each capability takes a `text_matching: TextMatchingConfig` keyword and builds
its engine from it per call (Eng. 4): text filters ignore case, accents and punctuation
(specs/009-text-value-matching/contracts/text-matching.md), empty results carry
`value_suggestions` (contracts/value-suggestions.md), and `inspect_schema` lists the
values of low-cardinality fields (contracts/schema-inspection.md).
"""

import pandas as pd

from data_access.dataset import Dataset
from data_access.exceptions import FieldNotFoundError, InvalidSortKeyError, NumericTypeError
from data_access.models import (
    AggregationRequest,
    AggregationResult,
    ContainsCondition,
    DiscoveryResult,
    EqualsCondition,
    FieldInfo,
    FilterCondition,
    RangeCondition,
    RowQueryResult,
    SchemaInspectionResult,
    SuggestedValue,
    ValueSuggestion,
)
from data_access.numeric import is_numeric_like
from data_access.query_engine import PandasQueryEngine, _is_missing
from data_access.text_matching import MatchRules, TextMatchingConfig, rank_candidates

SAMPLE_SIZE_CAP = 20
ROW_QUERY_CAP = 100


def discover_data_sources(dataset: Dataset) -> DiscoveryResult:
    return DiscoveryResult(sources=dataset.list_sources())


def inspect_schema(
    dataset: Dataset,
    identifier: str,
    *,
    text_matching: TextMatchingConfig = TextMatchingConfig(),
) -> SchemaInspectionResult:
    """Fields, types and a capped sample of one source.

    Fields, their order, `type` and `sample` come from the first SAMPLE_SIZE_CAP rows,
    as in 001. Each field also reports `distinct_count`, the distinct non-missing raw
    values over the **whole** source, and lists them all in `values` (code-point order)
    when there are at most `text_matching.value_list_threshold`; otherwise `values` is
    `None` (009 contracts/schema-inspection.md). No other size cap applies.
    """
    df = dataset.read(identifier)
    sample_df = df.head(SAMPLE_SIZE_CAP)
    threshold = text_matching.value_list_threshold

    observed_columns = [col for col in df.columns if bool(sample_df[col].notna().any())]
    fields: list[FieldInfo] = []
    for col in observed_columns:
        distinct = sorted({str(v) for v in df[col].unique() if not _is_missing(v)})
        fields.append(
            FieldInfo(
                name=col,
                type="numeric_like" if _is_numeric_field(df, col) else "text",
                distinct_count=len(distinct),
                values=distinct if len(distinct) <= threshold else None,
            )
        )

    sample = [
        {col: row[col] for col in observed_columns}
        for row in sample_df.to_dict(orient="records")
    ]

    return SchemaInspectionResult(
        identifier=identifier, fields=fields, sample=sample, value_list_threshold=threshold
    )


def query_rows(
    dataset: Dataset,
    identifier: str,
    filters: list[FilterCondition],
    *,
    text_matching: TextMatchingConfig = TextMatchingConfig(),
) -> RowQueryResult:
    """The rows of one source matching every filter (AND), capped at ROW_QUERY_CAP.

    Text filters follow `text_matching` (009 contracts/text-matching.md). When no row
    matches, `value_suggestions` lists, for each `equals`/`contains` condition that
    matches nothing on its own, the closest stored values of its field (009
    contracts/value-suggestions.md). A non-empty result never carries it.
    """
    df = dataset.read(identifier)
    _validate_filter_fields(identifier, df, filters)

    engine = _engine(text_matching)
    matched_df = engine.query_rows(df, filters)
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
        value_suggestions=(
            _value_suggestions(df, filters, engine, text_matching)
            if total_match_count == 0
            else None
        ),
    )


def aggregate_rows(
    dataset: Dataset,
    identifier: str,
    request: AggregationRequest,
    *,
    text_matching: TextMatchingConfig = TextMatchingConfig(),
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

    Text filters follow `text_matching` (009 contracts/text-matching.md). A result with
    zero groups carries `value_suggestions` exactly as `query_rows` would for the same
    filters (009 contracts/value-suggestions.md); a non-empty one never does.
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

    engine = _engine(text_matching)
    if df.empty:
        return AggregationResult(
            identifier=identifier,
            groups=[],
            total_group_count=0,
            truncated=False,
            value_suggestions=_value_suggestions(df, request.filters, engine, text_matching),
        )

    for spec in request.aggregates:
        if spec.function in ("sum", "mean", "min", "max") and not _is_numeric_field(
            df, spec.value_field
        ):
            raise NumericTypeError(identifier, spec.value_field)

    numeric_group_fields = frozenset(f for f in request.group_by if _is_numeric_field(df, f))
    all_groups = engine.aggregate(df, request, numeric_group_fields)
    total_group_count = len(all_groups)
    groups = all_groups if request.limit is None else all_groups[: request.limit]
    return AggregationResult(
        identifier=identifier,
        groups=groups,
        total_group_count=total_group_count,
        truncated=total_group_count > len(groups),
        value_suggestions=(
            _value_suggestions(df, request.filters, engine, text_matching)
            if total_group_count == 0
            else None
        ),
    )


def _engine(text_matching: TextMatchingConfig) -> PandasQueryEngine:
    """An engine per call, built from the injected config (Eng. 4)."""
    return PandasQueryEngine(MatchRules.from_config(text_matching))


def _value_suggestions(
    df: pd.DataFrame,
    filters: list[FilterCondition],
    engine: PandasQueryEngine,
    text_matching: TextMatchingConfig,
) -> list[ValueSuggestion] | None:
    """Suggestions for an empty result (009 contracts/value-suggestions.md).

    `None` when there is no `equals`/`contains` condition. Otherwise one entry, in
    request order, per text condition that matches no row of the **unfiltered** `df`
    on its own, with its field's closest non-missing stored values ranked by
    `rank_candidates`. An empty list means each text condition matches rows alone.
    """
    text_conditions = [
        c for c in filters if isinstance(c, (EqualsCondition, ContainsCondition))
    ]
    if not text_conditions:
        return None

    rules = MatchRules.from_config(text_matching)
    suggestions: list[ValueSuggestion] = []
    for condition in text_conditions:
        if not engine.query_rows(df, [condition]).empty:
            continue
        value_counts = {
            str(value): int(count)
            for value, count in df[condition.field].value_counts(dropna=True).items()
            if not _is_missing(value)
        }
        ranked = rank_candidates(
            value_counts, condition.value, rules, text_matching.max_suggestions
        )
        suggestions.append(
            ValueSuggestion(
                field=condition.field,
                op=condition.op,
                value=condition.value,
                candidates=[
                    SuggestedValue(value=value, overlap=overlap, row_count=row_count)
                    for value, overlap, row_count in ranked
                ],
            )
        )
    return suggestions


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
