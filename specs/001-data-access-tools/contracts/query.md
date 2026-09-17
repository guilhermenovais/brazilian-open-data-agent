# Contract: Filtered Row Query

```python
def query_rows(
    dataset: Dataset,
    identifier: str,
    filters: list[FilterCondition],
) -> RowQueryResult: ...
```

## Input

- `dataset: Dataset`
- `identifier: str` — a discovered identifier.
- `filters: list[FilterCondition]` — `EqualsCondition | ContainsCondition | RangeCondition`
  (data-model.md), combined with logical AND (FR-005). May be empty (returns up to
  `ROW_QUERY_CAP` unfiltered rows).

## Output

`RowQueryResult` (data-model.md) — `identifier`, `rows` (≤ `ROW_QUERY_CAP` = 100),
`returned_count`, `total_match_count`, `truncated`.

## Errors

| Condition | Exception |
|-----------|-----------|
| `identifier` not in the dataset | `DataSourceNotFoundError(identifier)` |
| `identifier` flagged unreadable | `UnreadableSourceError(identifier, detail)` |
| A filter references a field not present in the source | `FieldNotFoundError(identifier, field)` |
| A `RangeCondition` targets a field that is not `numeric_like` | `NumericTypeError(identifier, field)` |

## Behavioral requirements (traceability)

| Scenario | Requirement |
|----------|-------------|
| US3.1 | `EqualsCondition` → only exact matches. |
| US3.2 | `ContainsCondition` → case-insensitive substring match. |
| US3.3 | `RangeCondition` on a locale-formatted numeric field → matched by true numeric value (per research.md §3), not lexical comparison. |
| US3.4 | Multiple conditions → AND semantics; only rows satisfying all returned. |
| US3.5 | More matches than `ROW_QUERY_CAP` → `truncated=True`, `total_match_count` reflects the true total. |
| US3.6 | Filter on a nonexistent field → `FieldNotFoundError`, not an empty/misleading result. |
