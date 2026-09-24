# Contract: Aggregation

> **Superseded** by [`specs/007-aggregate-rows-enhancements/contracts/aggregation.md`](../../007-aggregate-rows-enhancements/contracts/aggregation.md).

```python
def aggregate_rows(
    dataset: Dataset,
    identifier: str,
    request: AggregationRequest,
) -> AggregationResult: ...
```

## Input

- `dataset: Dataset`
- `identifier: str` — a discovered identifier.
- `request: AggregationRequest` — `group_by: list[str]` (non-empty) + `aggregates:
  list[AggregateSpec]` (non-empty; `function` is `"count"` or `"sum"`) (data-model.md).

## Output

`AggregationResult` (data-model.md) — `identifier`, `groups: list[AggregationGroup]`. Empty
list when the source has no rows.

## Errors

| Condition | Exception |
|-----------|-----------|
| `identifier` not in the dataset | `DataSourceNotFoundError(identifier)` |
| `identifier` flagged unreadable | `UnreadableSourceError(identifier, detail)` |
| A `group_by` field or `value_field` doesn't exist in the source | `FieldNotFoundError(identifier, field)` |
| A `sum` aggregate targets a field that is not `numeric_like` | `NumericTypeError(identifier, field)` |

## Behavioral requirements (traceability)

| Scenario | Requirement |
|----------|-------------|
| US4.1 | Group by categorical field, `count` → each group's count matches true row count. |
| US4.2 | `sum` over a Brazilian-formatted value field → numerically correct sum. |
| US4.3 | More than one `group_by` field → results broken out by full combination of values. |
| US4.4 | `sum` on a non-numeric field → `NumericTypeError`, never a silently wrong number. |
| US4.5 | Source with no rows → empty `groups`, not an error. |
| US4.6 | Value field mixing `"1.234,56"`- and `"1,234.56"`-style rows → each value normalized per its own convention (research.md §3); sum numerically correct. |
