# Contract: Dataset Selection

```python
def select_dataset(
    question: str,
    selector: DatasetSelector,
    logger: SelectionLogger,
) -> DatasetSelectionResult: ...
```

Plain Python function (Constitution Engineering Principle 1 — no `pydantic-ai` import). A
future `@agent.tool` adapter wraps this 1:1, injecting `selector`/`logger` via
`RunContext[Deps]`.

## Input

- `question: str` — the user's question, exactly as received. Today's implementation
  (`StaticDatasetSelector`) does not inspect its content at all (spec Edge Case: relevance
  matching is out of scope for this feature) — it is accepted and recorded (FR-007) but not
  used to choose between datasets.
- `selector: DatasetSelector` — the injected selection strategy (data-model.md). Callers
  compose the concrete implementation (e.g. `StaticDatasetSelector(briefing_source, locator)`)
  themselves; `select_dataset` has no built-in default.
- `logger: SelectionLogger` — the injected usage recorder (data-model.md).

## Output

`DatasetSelectionResult` (data-model.md) — `dataset_key`, `briefing`, and `dataset` (a ready-
to-use `data_access.dataset.Dataset`, research.md §6).

## Side effect

Exactly one `DatasetSelectionLogEntry` (question, dataset_key, timestamp) is passed to
`logger.log(...)` per call, after the selector returns successfully (FR-007/SC-005). No log
entry is written if `selector.select(...)` raises.

## Errors

| Condition | Exception |
|-----------|-----------|
| The selected key has no matching folder under the datasets directory | `DatasetNotFoundError(key)` |
| No briefings are registered at all | `NoBriefingsAvailableError()` |

See `errors.md` for the full exception hierarchy.

## Behavioral requirements (traceability)

| Scenario / Requirement | Behavior |
|-------------------------|----------|
| US1 Acceptance Scenario 1 | A question about AEB/MCTIC budget execution → result identifies `orcamentos-aeb-csv`, includes its briefing, and its `dataset` resolves to the correct folder. |
| US1 Acceptance Scenario 2 | An unrelated question (e.g. weather) → same result as above; no "no match" behavior exists in this phase (FR-003, FR-006). |
| US2 Acceptance Scenario 1 | Given the briefing key `orcamentos-aeb-csv`, the result's `dataset` resolves to the `orcamentos-aeb-csv` folder under the datasets directory (FR-004). |
| FR-002 | Every result includes both the briefing text and the dataset's location (`dataset`). |
| FR-005 | A key with no matching dataset folder raises `DatasetNotFoundError`, never a partial/invalid result. |
| FR-007 / SC-005 | Every call that returns successfully produces exactly one corresponding log entry. |
