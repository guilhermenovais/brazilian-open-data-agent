# Contract: Discovery

```python
def discover_data_sources(dataset: Dataset) -> DiscoveryResult: ...
```

Plain Python function (Constitution Engineering Principle 1 — no `pydantic-ai` import). A
future `@agent.tool` adapter wraps this 1:1.

## Input

- `dataset: Dataset` — the internal abstraction over the dataset's root storage (see
  data-model.md). Caller does not know or provide any physical path beyond what was used to
  construct `Dataset` at session setup.

## Output

`DiscoveryResult` (data-model.md) — `sources: list[DataSourceInfo]`. Empty list when the
dataset has no data sources.

## Errors

| Condition | Exception |
|-----------|-----------|
| Two or more physical sources resolve to the same identifier | `IdentifierCollisionError(identifier, physical_paths)` |

A parse failure on an individual source is **not** an error here — it is represented as
`DataSourceInfo(readable=False)` in the result (FR-001a); discovery of other sources is
unaffected.

## Behavioral requirements (traceability)

| Scenario | Requirement |
|----------|-------------|
| US1.1 | All CSV/JSON sources listed with identifier + format. |
| US1.2 | Non-data files (e.g. `README.md`) excluded. |
| US1.3 | Empty dataset → empty list, not an error. |
| US1.4 | Unparseable source still listed, `readable=False`; others unaffected. |
| US1.5 | Nested subfolders flattened into one list; identifiers carry relative path (e.g. `"reports/2024/sales.csv"`). |
| FR-012a | Colliding identifiers → whole call fails naming the colliding sources; neither is listed. |
