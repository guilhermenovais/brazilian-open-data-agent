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


class SchemaInspectionResult(BaseModel):
    identifier: str
    fields: list[FieldInfo]
    sample: list[dict[str, str | None]]


class EqualsCondition(BaseModel):
    field: str
    op: Literal["equals"] = "equals"
    value: str


class ContainsCondition(BaseModel):
    field: str
    op: Literal["contains"] = "contains"
    value: str


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


class RowQueryResult(BaseModel):
    identifier: str
    rows: list[dict[str, str | None]]
    returned_count: int
    total_match_count: int
    truncated: bool


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
