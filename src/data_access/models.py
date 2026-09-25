"""Pydantic I/O models crossing the data access tool layer's capability boundary.

Every tool input/output is a validated pydantic model (Constitution Engineering
Principle 5) — no untyped dicts cross this boundary.
"""

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class DataSourceInfo(BaseModel):
    identifier: str = Field(min_length=1)
    format: Literal["csv", "json"]
    readable: bool


class DiscoveryResult(BaseModel):
    sources: list[DataSourceInfo]


class FieldInfo(BaseModel):
    name: str
    type: Literal["numeric_like", "text"]
    distinct_count: int = Field(
        description="Distinct non-missing raw values of this field across the **whole** source."
    )
    values: list[str] | None = Field(
        description=(
            "All those values, raw, sorted by code point, when `distinct_count <= "
            "value_list_threshold`. Otherwise `null` (not listed: too many values)."
        )
    )


class SchemaInspectionResult(BaseModel):
    identifier: str
    fields: list[FieldInfo]
    sample: list[dict[str, str | None]]
    value_list_threshold: int = Field(
        description="The threshold used, so a `null` `values` reads as 'more than N values'."
    )


class EqualsCondition(BaseModel):
    field: str
    op: Literal["equals"] = "equals"
    value: str = Field(
        description="Whole value, compared ignoring case, accents and punctuation."
    )


class ContainsCondition(BaseModel):
    field: str
    op: Literal["contains"] = "contains"
    value: str = Field(
        description=(
            "Every word (filler words like 'de', 'do' skipped) must start a word of the "
            "stored value, in any order; case, accents and punctuation ignored."
        )
    )


class RangeCondition(BaseModel):
    field: str
    op: Literal["range"] = "range"
    min: float | None = None
    max: float | None = None

    def model_post_init(self, __context: object) -> None:
        if self.min is None and self.max is None:
            raise ValueError("RangeCondition requires at least one of min/max to be set")


FilterCondition = Annotated[
    Union[EqualsCondition, ContainsCondition, RangeCondition],
    Field(discriminator="op"),
]


class SuggestedValue(BaseModel):
    value: str = Field(description="A distinct stored value of the field, exactly as stored.")
    overlap: int = Field(
        ge=1,
        description="Query words of the condition that start a word or the acronym of `value`.",
    )
    row_count: int = Field(ge=1, description="Rows of the source holding exactly this value.")


class ValueSuggestion(BaseModel):
    """One `equals`/`contains` condition that matches no row of the source on its own."""

    field: str
    op: Literal["equals", "contains"]
    value: str
    candidates: list[SuggestedValue] = Field(
        description=(
            "At most `max_suggestions`. Ordered by `overlap` desc, `row_count` desc, `value` "
            "asc (code point). **Empty** means 'no close values found'."
        )
    )


def _is_none(value: object) -> bool:
    return value is None


class RowQueryResult(BaseModel):
    identifier: str
    rows: list[dict[str, str | None]]
    returned_count: int
    total_match_count: int
    truncated: bool
    # Only on an empty result with text conditions (009 contracts/value-suggestions.md);
    # absent from the serialized form otherwise, so other results serialize as before.
    value_suggestions: list[ValueSuggestion] | None = Field(default=None, exclude_if=_is_none)


AggregateFunction = Literal["count", "sum", "mean", "min", "max", "count_distinct"]


class AggregateSpec(BaseModel):
    value_field: str
    function: AggregateFunction = Field(
        description=(
            "One of count, sum, mean, min, max, count_distinct. sum/mean/min/max need a "
            "numeric-like value_field; count and count_distinct accept any field. The "
            "result key is '<function>_<value_field>', e.g. 'sum_valor'."
        )
    )


class SortKey(BaseModel):
    key: str = Field(
        description=(
            "A group_by field or a result key '<function>_<value_field>' of a requested "
            "aggregate. A name that is both refers to the grouping field."
        )
    )
    direction: Literal["asc", "desc"] = Field(
        default="asc", description="'asc' (default) or 'desc'."
    )


class AggregationRequest(BaseModel):
    group_by: list[str] = Field(min_length=1)
    aggregates: list[AggregateSpec] = Field(min_length=1)
    filters: list[FilterCondition] = Field(
        default_factory=list,
        description=(
            "Same conditions as query_rows (equals / contains / range), combined with AND "
            "and applied before grouping: only matching rows are grouped and aggregated."
        ),
    )
    order_by: list[SortKey] = Field(
        default_factory=list,
        description=(
            "Applied in list order; later keys break ties of earlier ones. Missing values "
            "sort last in both directions. Without order_by, groups are sorted ascending "
            "by their grouping values."
        ),
    )
    limit: int | None = Field(
        default=None,
        ge=1,
        description="Maximum number of groups to return, applied after ordering.",
    )


class AggregationGroup(BaseModel):
    group_values: dict[str, str | None]
    results: dict[str, float | int | None]


class AggregationResult(BaseModel):
    identifier: str
    groups: list[AggregationGroup]
    total_group_count: int
    truncated: bool
    # Same rule as RowQueryResult.value_suggestions.
    value_suggestions: list[ValueSuggestion] | None = Field(default=None, exclude_if=_is_none)
