# Contract: Schema Inspection

```python
def inspect_schema(dataset: Dataset, identifier: str) -> SchemaInspectionResult: ...
```

## Input

- `dataset: Dataset`
- `identifier: str` — an identifier previously returned by `discover_data_sources` (FR-014:
  no hidden knowledge required beyond having called discovery first).

## Output

`SchemaInspectionResult` (data-model.md) — `identifier`, `fields: list[FieldInfo]`, `sample`
(≤ `SAMPLE_SIZE_CAP` = 20 raw records).

## Errors

| Condition | Exception |
|-----------|-----------|
| `identifier` not in the dataset | `DataSourceNotFoundError(identifier)` |
| `identifier` is flagged `readable=False` at discovery, or fails to parse now | `UnreadableSourceError(identifier, detail)` |

## Behavioral requirements (traceability)

| Scenario | Requirement |
|----------|-------------|
| US2.1 | 10,000-row CSV → all field names + sample capped at `SAMPLE_SIZE_CAP`, not the full file. |
| US2.2 | Heterogeneous JSON records → union of fields observed across the sample. |
| US2.3 | Brazilian-formatted field (`"1.234,56"`) shown unchanged in the sample; field flagged `numeric_like`. |
| US2.4 | Unknown identifier → `DataSourceNotFoundError`, no partial/fabricated data. |
| US2.5 | Unreadable source → `UnreadableSourceError`, no partial/fabricated data. |
| SC-002 | Fields + sample returned in one call; no separate full scan needed. |
