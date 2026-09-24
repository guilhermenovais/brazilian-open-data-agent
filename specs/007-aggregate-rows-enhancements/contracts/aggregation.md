# Contract: Aggregation (revision of `001` contracts/aggregation.md)

```python
def aggregate_rows(
    dataset: Dataset,
    identifier: str,
    request: AggregationRequest,
) -> AggregationResult: ...
```

Plain Python in `data_access.capabilities`, with no `pydantic-ai` import (FR-019).

## Input

- `dataset: Dataset`
- `identifier: str`: a discovered identifier.
- `request: AggregationRequest` (data-model.md):
  - `group_by` (non-empty), `aggregates` (non-empty; `function` ∈ `count`, `sum`, `mean`,
    `min`, `max`, `count_distinct`).
  - `filters` (optional): the same `FilterCondition`s as `query_rows`, combined with AND.
  - `order_by` (optional): `SortKey(key, direction="asc"|"desc")` list.
  - `limit` (optional): an integer ≥ 1. Pydantic rejects smaller values when the request is built.

## Output

`AggregationResult`: `identifier`, `groups` (ordered, at most `limit` entries),
`total_group_count` (groups before the limit), `truncated`.

Pipeline: filter → group → aggregate → order → limit.

## Errors

Raised in this order (research.md §3):

| # | Condition | Exception |
|---|-----------|-----------|
| 1 | `identifier` not in the dataset | `DataSourceNotFoundError(identifier)` |
| 1 | `identifier` flagged unreadable | `UnreadableSourceError(identifier, detail)` |
| 2 | A `group_by` field or `value_field` doesn't exist | `FieldNotFoundError(identifier, field)` |
| 3 | A filter field doesn't exist | `FieldNotFoundError(identifier, field)` |
| 3 | A `range` filter targets a field that isn't numeric-like | `NumericTypeError(identifier, field)` |
| 4 | An `order_by` key is neither a grouping field nor a requested result key | `InvalidSortKeyError(identifier, key, valid_keys)` |
| — | *Source has no rows → return zero groups (no further checks)* | — |
| 5 | `sum`/`mean`/`min`/`max` targets a field that isn't numeric-like (whole source) | `NumericTypeError(identifier, field)` |

`limit < 1` never reaches the function: `AggregationRequest` construction raises
`pydantic.ValidationError`.

## Behavioral requirements (traceability)

Existing scenarios US4.1–US4.6 from `001` keep passing, with no change except for group order
(FR-016, SC-001).

| Scenario | Requirement |
|----------|-------------|
| 007 US1.1 | `ano equals 2023` filter → each group's `sum` includes only 2023 rows. |
| 007 US1.2 | Several conditions → AND, the same as `query_rows`. |
| 007 US1.3 | Filters match nothing → `groups == []`, `total_group_count == 0`, no error. |
| 007 US1.4 | Unknown filter field → `FieldNotFoundError`. |
| 007 US1.5 | Range filter on a text field → `NumericTypeError`. |
| 007 US1.6 | No filters → same groups/values as before. |
| 007 US2.1 | "10","20","30" → `mean` 20, `min` 10, `max` 30. |
| 007 US2.2 | "1.234,56"-style values parsed the same way `sum` parses them. |
| 007 US2.3 | Missing values ignored, not counted as zero. |
| 007 US2.4 | All values missing → `mean`/`min`/`max` are `None`. |
| 007 US2.5 | `mean`/`min`/`max` on a text field → `NumericTypeError`, even when the filters match nothing. |
| 007 US2.6 | "A","B","A", missing → `count_distinct` = 2. |
| 007 US2.7 | `count_distinct` accepted on numeric-like and text fields. |
| 007 US3.1 | `order_by sum_valor desc`, `limit 5` over 50 groups → the top 5 in descending order. |
| 007 US3.2 | Order by a text grouping field → code-point order. Numeric-like grouping field → numeric order ("2" before "10"). |
| 007 US3.3 | Several keys → lexicographic by key, with later keys breaking ties. |
| 007 US3.4 | Missing sort values last, both directions. |
| 007 US3.5 | `limit` < group count → `total_group_count` = full count, `truncated` = True. |
| 007 US3.6 | `limit` with no `order_by` → first N groups in the default order, `truncated` = True. |
| 007 US3.7 | Invalid sort key → `InvalidSortKeyError` naming the key and listing the valid keys. |
| 007 US3.8 | `limit` 0 or negative → `ValidationError`. |
| Edge | Empty source → zero groups for every function. Unparseable numeric values skipped. `limit` > group count → not truncated. Duplicate spec → one key. |
