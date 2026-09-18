# Quickstart: Validating the Dataset Selector

This is a runnable validation guide, not implementation code — it proves the feature works
end-to-end once built. See `data-model.md` for exact model shapes and `contracts/` for
behavior.

## Prerequisites

- Python 3.11+, project virtualenv installed (`pandas`, `pydantic`, `pytest`).
- The real `data/briefings/orcamentos-aeb-csv.md` and `data/datasets/orcamentos-aeb-csv/`
  already present in the repo (used for US1's scenarios).
- A test fixture pair for US2/isolation tests, e.g.
  `tests/fixtures/dataset_selector/briefings/sample-key.md` and
  `tests/fixtures/dataset_selector/datasets/sample-key/data.csv`.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Scenario 1 — Always resolves to the one registered dataset (US1)

```python
from dataset_selector.briefing import FileBriefingSource
from dataset_selector.locator import LocalDatasetLocator
from dataset_selector.selector import StaticDatasetSelector
from dataset_selector.usage_log import JsonlSelectionLogger
from dataset_selector.capabilities import select_dataset

selector = StaticDatasetSelector(
    briefing_source=FileBriefingSource("data/briefings"),
    locator=LocalDatasetLocator("data/datasets"),
)
logger = JsonlSelectionLogger("data/logs/dataset_selections.jsonl")

for question in (
    "Quanto foi empenhado pela AEB em 2015?",
    "What's the weather like today?",  # unrelated question — same result (FR-006)
):
    result = select_dataset(question, selector=selector, logger=logger)
    assert result.dataset_key == "orcamentos-aeb-csv"
    assert "AEB" in result.briefing
```

**Expected outcome**: both calls return the same `dataset_key`/`briefing`, regardless of the
question's relevance — no "no match" behavior exists in this phase.

## Scenario 2 — The result's `dataset` is immediately usable with the existing tool layer (US2, research.md §6)

```python
from data_access.capabilities import discover_data_sources

sources = discover_data_sources(result.dataset)
assert any(s.identifier.endswith("tb_geral.csv") for s in sources.sources)
```

**Expected outcome**: `result.dataset` needs no wrapping or adaptation — it's the same
`data_access.dataset.Dataset` the `001-data-access-tools` capabilities already consume.

## Scenario 3 — Briefing key resolves to the correct folder (US2)

```python
assert result.dataset_key == "orcamentos-aeb-csv"
# result.dataset was constructed from data/datasets/orcamentos-aeb-csv/
```

## Scenario 4 — Missing dataset folder is a clear error, not a broken result (FR-005)

```python
import pytest
from dataset_selector.locator import LocalDatasetLocator
from dataset_selector.exceptions import DatasetNotFoundError

locator = LocalDatasetLocator("data/datasets")
with pytest.raises(DatasetNotFoundError):
    locator.locate("does-not-exist")
```

## Scenario 5 — Every selection is logged (FR-007 / SC-005)

```python
import json

log_path = "data/logs/dataset_selections.jsonl"
before = sum(1 for _ in open(log_path)) if __import__("os").path.exists(log_path) else 0

select_dataset("Any question", selector=selector, logger=logger)

lines = open(log_path).readlines()
assert len(lines) == before + 1
entry = json.loads(lines[-1])
assert entry["dataset_key"] == "orcamentos-aeb-csv"
assert "question" in entry and "timestamp" in entry
```

## Running the full contract suite

```bash
pytest tests/contract/dataset_selector -v
pytest tests/unit/dataset_selector -v
pyright src/
```

**Done when**: all contract tests (one per Acceptance Scenario in `spec.md`) pass, unit tests
for `LocalDatasetLocator`, `FileBriefingSource`, and `JsonlSelectionLogger` pass in isolation,
and `pyright` reports zero errors.
