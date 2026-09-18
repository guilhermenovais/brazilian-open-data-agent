# Phase 1 Data Model: Dataset Selector

I/O-crossing shapes are pydantic v2 `BaseModel`s (Constitution Engineering Principle 5).
Internal-only helper types (the `Protocol`s and their implementations) are plain Python and
are documented here for completeness but are not part of the external contract.

## Entities

### DatasetSelectionResult *(select_dataset output)*

| Field         | Type      | Notes |
|---------------|-----------|-------|
| `dataset_key` | `str`     | Non-empty. The briefing's file stem (FR-004); e.g. `"orcamentos-aeb-csv"`. |
| `briefing`    | `str`     | The briefing's full raw text content, as read from its `.md` file (FR-002). |
| `dataset`     | `data_access.dataset.Dataset` | Reused as-is from `001-data-access-tools` (research.md §6) — already a fully-usable handle onto the dataset's data files, ready to pass directly into `data_access.capabilities.*`. Not a pydantic model; requires `model_config = ConfigDict(arbitrary_types_allowed=True)` on this model. |

### DatasetSelectionLogEntry *(one recorded selection decision — FR-007)*

| Field         | Type       | Notes |
|---------------|------------|-------|
| `question`    | `str`      | The user's question exactly as passed to `select_dataset`. |
| `dataset_key` | `str`      | The key of the dataset that was selected for it. |
| `timestamp`   | `datetime` | UTC, captured at the moment of the decision (`datetime.now(timezone.utc)`). |

## Errors (raised, not returned — see research.md §8)

| Exception                  | Raised when | Carries |
|-----------------------------|-------------|---------|
| `DatasetNotFoundError`      | A key resolved from `BriefingSource.list_keys()` has no matching folder under the datasets directory (FR-005). | `key` |
| `BriefingNotFoundError`     | `BriefingSource.get(key)` is called directly with a key that has no `.md` file. Defensive only — never reachable through `select_dataset`'s own flow, since it only ever asks for keys `list_keys()` itself returned. | `key` |
| `NoBriefingsAvailableError` | `BriefingSource.list_keys()` returns an empty list — no dataset is registered at all. | — |

All three subclass `DatasetSelectorError`, this module's base exception (mirrors
`data_access.exceptions.DataAccessError`).

## Internal (non-contract) types

### `DatasetSelector` (Protocol) — the axis expected to vary (research.md §2)

```python
class DatasetSelector(Protocol):
    def select(self, question: str) -> DatasetSelectionResult: ...
```

**`StaticDatasetSelector`** *(today's only implementation)*: takes a `BriefingSource` and a
`DatasetLocator`. `select(question)` ignores `question`'s content entirely (spec Edge Case:
relevance matching is out of scope) and always returns the lexicographically-first key from
`briefing_source.list_keys()` (research.md §3) — never a hardcoded dataset name. Raises
`NoBriefingsAvailableError` if no keys are registered.

A future, smarter implementation (subagents/RAG per the spec's own Input text) is written
against this same `Protocol` and requires no change to `select_dataset` or its callers
(SC-004).

### `DatasetLocator` (Protocol) — resolves a key to a physical folder (research.md §4)

```python
class DatasetLocator(Protocol):
    def locate(self, key: str) -> Path: ...
```

**`LocalDatasetLocator`** *(today's only implementation)*: constructed with a
`datasets_root`; `locate(key)` returns `datasets_root / key` if that folder exists, else
raises `DatasetNotFoundError(key)`.

A future `OnDemandDatasetLocator` (download-on-miss, then return the local cache path — per
spec Assumptions) implements the same `Protocol`.

### `BriefingSource` (Protocol) — reads briefing content and enumerates keys (research.md §5)

```python
class BriefingSource(Protocol):
    def list_keys(self) -> list[str]: ...
    def get(self, key: str) -> str: ...
```

**`FileBriefingSource`** *(today's only implementation)*: constructed with a
`briefings_root`; `list_keys()` returns the sorted `.stem`s of every `*.md` file directly
under it; `get(key)` returns `(briefings_root / f"{key}.md").read_text()`, or raises
`BriefingNotFoundError(key)` if that file doesn't exist.

### `SelectionLogger` (Protocol) — records usage data (research.md §7)

```python
class SelectionLogger(Protocol):
    def log(self, entry: DatasetSelectionLogEntry) -> None: ...
```

**`JsonlSelectionLogger`** *(today's only implementation)*: constructed with a `log_path`;
`log(entry)` appends `entry.model_dump_json() + "\n"` to that file, creating parent
directories on first use.

## Relationships

```
DatasetSelector.select(question) --> DatasetSelectionResult
    DatasetSelectionResult.dataset_key --derived from--> BriefingSource.list_keys()[0]
    DatasetSelectionResult.briefing    --derived from--> BriefingSource.get(dataset_key)
    DatasetSelectionResult.dataset     --derived from--> Dataset(DatasetLocator.locate(dataset_key))

select_dataset(question, selector, logger):
    result = selector.select(question)
    logger.log(DatasetSelectionLogEntry(question, result.dataset_key, now()))
    return result
```

## Public capability

```python
def select_dataset(
    question: str,
    selector: DatasetSelector,
    logger: SelectionLogger,
) -> DatasetSelectionResult: ...
```

The single public entry point (Constitution Engineering Principle 1 — no `pydantic-ai`
import; a future `@agent.tool` adapter wraps this 1:1, injecting `selector`/`logger` via
`RunContext[Deps]`).
