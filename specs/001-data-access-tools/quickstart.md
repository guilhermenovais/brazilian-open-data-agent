# Quickstart: Validating the Data Access Tool Layer

This is a runnable validation guide, not implementation code — it proves the feature works
end-to-end once built. See `data-model.md` for exact model shapes and `contracts/` for
per-capability behavior.

## Prerequisites

- Python 3.11+, project virtualenv installed (`pandas`, `pydantic`, `pytest`).
- A local test dataset folder, e.g. `tests/fixtures/sample_dataset/`, containing:
  - `customers.csv` — plain CSV, US-style numeric column.
  - `orders/2024/sales.csv` — nested subfolder; `amount` column mixes Brazilian-style
    (`"1.234,56"`) and US-style (`"1,234.56"`) values row-to-row, per value, within the same
    column (exercises US4 Acceptance Scenario 6 / FR-010).
  - `products.json` — array of flat, heterogeneous objects.
  - `broken.csv` — deliberately malformed (unclosed quote) to exercise the unreadable path.
  - `README.md` — non-data file, must never appear in discovery output.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Scenario 1 — Discovery (US1)

```python
from data_access.dataset import Dataset
from data_access.capabilities import discover_data_sources

dataset = Dataset(root_path="tests/fixtures/sample_dataset")
result = discover_data_sources(dataset)

assert {s.identifier for s in result.sources} == {
    "customers.csv", "orders/2024/sales.csv", "products.json", "broken.csv",
}
assert all(s.identifier != "README.md" for s in result.sources)
broken = next(s for s in result.sources if s.identifier == "broken.csv")
assert broken.readable is False
```

**Expected outcome**: 4 sources listed (README.md excluded), `broken.csv` present with
`readable=False`, `orders/2024/sales.csv` identifier reflects its subfolder path.

## Scenario 2 — Schema inspection (US2)

```python
from data_access.capabilities import inspect_schema

schema = inspect_schema(dataset, "orders/2024/sales.csv")
amount_field = next(f for f in schema.fields if f.name == "amount")
assert amount_field.type == "numeric_like"
assert any("1.234,56" in str(r.get("amount")) for r in schema.sample)
assert len(schema.sample) <= 20
```

**Expected outcome**: field list + ≤20-row sample; Brazilian-formatted value visible
unchanged; field still classified `numeric_like`.

## Scenario 3 — Filtered row query (US3)

```python
from data_access.capabilities import query_rows
from data_access.models import RangeCondition

result = query_rows(
    dataset, "orders/2024/sales.csv",
    filters=[RangeCondition(field="amount", op="range", min=1000, max=2000)],
)
assert result.returned_count == result.total_match_count or result.truncated
```

**Expected outcome**: only rows whose true numeric `amount` (after locale normalization)
falls in `[1000, 2000]`, regardless of `.`/`,` formatting in the source.

## Scenario 4 — Aggregation (US4)

```python
from data_access.capabilities import aggregate_rows
from data_access.models import AggregationRequest, AggregateSpec

agg = aggregate_rows(
    dataset, "orders/2024/sales.csv",
    AggregationRequest(
        group_by=["region"],
        aggregates=[AggregateSpec(value_field="amount", function="sum")],
    ),
)
assert all("sum_amount" in g.results for g in agg.groups)
```

**Expected outcome**: one group per distinct `region`, each with a numerically correct
`sum_amount` regardless of mixed locale formatting within the column.

## Scenario 5 — Errors are clear, never silent (SC-005)

```python
import pytest
from data_access.exceptions import DataSourceNotFoundError, UnreadableSourceError

with pytest.raises(DataSourceNotFoundError):
    inspect_schema(dataset, "does-not-exist.csv")

with pytest.raises(UnreadableSourceError):
    inspect_schema(dataset, "broken.csv")
```

## Running the full contract suite

```bash
pytest tests/contract -v
pytest tests/unit -v
pyright src/
```

**Done when**: all contract tests (one per Acceptance Scenario in `spec.md`) pass, unit
tests for `numeric.py`'s locale parsing and `Dataset`'s collision detection pass, and
`pyright` reports zero errors.
