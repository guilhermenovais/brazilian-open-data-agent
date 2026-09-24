# Data Model: Richer Aggregation

**Feature**: `007-aggregate-rows-enhancements` | **Date**: 2026-09-24

All models live in `src/data_access/models.py` (pydantic v2, no `pydantic-ai` import).
Unchanged models (`EqualsCondition`, `ContainsCondition`, `RangeCondition`, `FilterCondition`,
`RowQueryResult`, …) are reused as they are.

## AggregateFunction *(new type alias)*

```python
AggregateFunction = Literal["count", "sum", "mean", "min", "max", "count_distinct"]
```

| Function | Accepted value fields | Result type | Group with no usable value |
|----------|-----------------------|-------------|----------------------------|
| `count` | any | `int` | n/a |
| `sum` | numeric-like | `float` | `0.0` (unchanged) |
| `mean` | numeric-like | `float \| None` | `None` |
| `min` | numeric-like | `float \| None` | `None` |
| `max` | numeric-like | `float \| None` | `None` |
| `count_distinct` | any | `int` | `0` |

"Numeric-like" is decided on the **unfiltered** source by the `inspect_schema` rule
(research.md §2). "Missing" is `None`/NaN or a whitespace-only string (research.md §4).

## AggregateSpec *(changed)*

| Field | Type | Rules |
|-------|------|-------|
| `value_field` | `str` | Must exist in the source → else `FieldNotFoundError`. |
| `function` | `AggregateFunction` | Was `Literal["count", "sum"]`. |

**Result key**: `f"{function}_{value_field}"` (unchanged convention, FR-009). Two specs with
the same function and field produce one key.

## SortKey *(new)*

| Field | Type | Default | Rules |
|-------|------|---------|-------|
| `key` | `str` | (required) | Must be a `group_by` field or a result key of `aggregates`. Else `InvalidSortKeyError`. If a name is both, it refers to the grouping field (research.md §6). |
| `direction` | `Literal["asc", "desc"]` | `"asc"` | |

## AggregationRequest *(changed)*

| Field | Type | Default | Rules |
|-------|------|---------|-------|
| `group_by` | `list[str]` | (required) | `min_length=1` (unchanged). |
| `aggregates` | `list[AggregateSpec]` | (required) | `min_length=1` (unchanged). |
| `filters` | `list[FilterCondition]` | `[]` | **New.** AND-combined, and validated like `query_rows` (FR-001–FR-003). |
| `order_by` | `list[SortKey]` | `[]` | **New.** Applied in list order. Later keys break ties (FR-010, FR-011). |
| `limit` | `int \| None` | `None` | **New.** `ge=1`. Pydantic rejects `0` and negative values (FR-013). |

All new fields carry `Field(description=...)` text, which the agent sees (FR-017).

**Processing pipeline** (FR-014): *filter → group → aggregate → order → limit*.

## AggregationGroup *(changed)*

| Field | Type | Change |
|-------|------|--------|
| `group_values` | `dict[str, str \| None]` | Unchanged. Values reported as text, `None` for a missing key. |
| `results` | `dict[str, float \| int \| None]` | Widened to allow `None` (FR-007). |

## AggregationResult *(changed)*

| Field | Type | Change |
|-------|------|--------|
| `identifier` | `str` | Unchanged. |
| `groups` | `list[AggregationGroup]` | Now always in a deterministic order (FR-011, FR-016). At most `limit` entries. |
| `total_group_count` | `int` | **New, required.** Number of groups after filtering and before the limit. |
| `truncated` | `bool` | **New, required.** `total_group_count > len(groups)`. |

Invariants: `len(groups) <= total_group_count`; `truncated` ⇔ `limit is not None and total_group_count > limit`;
an empty source or no matching rows ⇒ `groups == []`, `total_group_count == 0`, `truncated is False`.

## Group ordering *(behavior, no model)*

1. **Default order**: ascending by each `group_by` field in turn. Numeric-like grouping fields
   are compared as parsed numbers and text fields by Unicode code point. Missing or unparseable
   values go last, and the raw text breaks any remaining ties.
2. **`order_by` keys** are applied on top, first key most significant. Missing values go last
   whatever the direction.

Details: research.md §7.

## InvalidSortKeyError *(new, `src/data_access/exceptions.py`)*

```python
class InvalidSortKeyError(DataAccessError):
    identifier: str
    key: str
    valid_keys: list[str]   # group_by fields, then result keys, in request order, no duplicates
```

Message: `Sort key 'x' is not valid for data source 'id'; valid keys: ['uf', 'sum_valor']`.
It is a `DataAccessError`, so `qa_agent.tools.aggregate_rows` already turns it into
`ModelRetry` (FR-018).

## QueryEngine protocol *(changed signature, `src/data_access/query_engine.py`)*

```python
def aggregate(
    self,
    df: pd.DataFrame,                        # unfiltered source frame
    request: AggregationRequest,             # engine applies request.filters itself
    numeric_group_fields: frozenset[str],    # group_by fields classified numeric-like by the capability
) -> list[AggregationGroup]: ...            # every group, ordered; no limit applied
```

`query_rows` is unchanged.
