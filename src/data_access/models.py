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


class AggregateSpec(BaseModel):
    value_field: str
    function: Literal["count", "sum"]


class AggregationRequest(BaseModel):
    group_by: list[str] = Field(min_length=1)
    aggregates: list[AggregateSpec] = Field(min_length=1)


class AggregationGroup(BaseModel):
    group_values: dict[str, str | None]
    results: dict[str, float | int]


class AggregationResult(BaseModel):
    identifier: str
    groups: list[AggregationGroup]
