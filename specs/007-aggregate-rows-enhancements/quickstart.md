# Quickstart: Validating Richer Aggregation

**Feature**: `007-aggregate-rows-enhancements`

## Prerequisites

- Project venv with dev extras: `pip install -e ".[dev]"`.
- For the testset comparison (SC-004) only: model credentials, the same as for any
  `testset_runner` run.

## 1. Automated checks (the CI gate)

```bash
pytest tests/contract tests/unit -v
pyright src/
```

Expected: everything passes. Specifically:

| Test file | Proves |
|-----------|--------|
| `tests/contract/data_access/test_aggregation.py` | The existing US4.1–US4.6 cases pass unchanged (SC-001). The new cases cover every row of [contracts/aggregation.md](./contracts/aggregation.md): 007 US1.x (filters), US2.x (functions), US3.x (order/limit) and the edge cases. |
| `tests/unit/data_access/test_query_engine.py` *(new)* | Engine-level ordering: missing values last in both directions, stable tie-breaking across keys, numeric vs code-point ordering of grouping values, a default order that doesn't depend on source row order (the same rows shuffled give the same output). |
| `tests/unit/qa_agent/test_tools_description.py` *(new)* | The `aggregate_rows` tool description and schema document the filters, the six functions, the result-key naming, `order_by` and `limit` (FR-017; [contracts/aggregate-rows-tool.md](./contracts/aggregate-rows-tool.md)). |
| `tests/contract/qa_agent/*` | Scripted `aggregate_rows` calls still work, because the new fields are optional. |

The new contract cases use a small fixture source added under
`tests/fixtures/data_access/sample_dataset/` with columns for a year, a text grouping field,
a numeric-like grouping field (`mes`, "1"…"12"), a Brazilian-formatted value field with
missing cells, and a repeated text field for `count_distinct`. Expected values are computed
by hand and written as literals in the tests (SC-002).

## 2. Direct capability call (no agent)

This shows FR-019: the harness can call the capability without the agent framework.

```bash
python - <<'EOF'
from data_access.capabilities import aggregate_rows
from data_access.dataset import Dataset
from data_access.models import AggregateSpec, AggregationRequest, SortKey, EqualsCondition

ds = Dataset("data/datasets/orcamentos-aeb-csv")
src = ds.list_sources()[0].identifier   # pick a source with a year and a value column
print(src)
EOF
```

Then, with real field names taken from `inspect_schema` for that source, run one request that
uses all of the new parameters at once. Example: filter to one year, `sum` + `mean` +
`count_distinct`, `order_by` the sum descending, `limit=3`.

Expected:
- 3 groups, with sums in non-increasing order,
- `total_group_count` ≥ 3, and `truncated` is `True` when there were more,
- the sums equal a `query_rows` over the same filter summed by hand for the top group.

Also check that the following raise the documented errors:
- `order_by=[SortKey(key="nope")]` → `InvalidSortKeyError`, whose message lists the valid keys,
- `mean` on a text field → `NumericTypeError`,
- `AggregationRequest(..., limit=0)` → `pydantic.ValidationError`.

## 3. Agent end-to-end (SC-003)

```bash
python -m web_ui.cli   # chat web UI; uses the same QA_AGENT_* env vars as the testset runner
```

In the chat, ask a scoped top-N question for the AEB budget dataset, for example "Quais foram as 3 ações
com maior valor orçado em 2023?". In the run log (`data/logs/qa_agent_runs.jsonl`), the
answer's retrieval trace should show **one** `aggregate_rows` call with `filters`,
`order_by` (`desc`) and `limit`, with no `query_rows` call followed by numbers the agent
worked out itself.

## 4. Testset before/after (SC-004)

```bash
# at the pre-feature commit (baseline)
git stash -u && git checkout 6636991
python -m testset_runner.cli run --testset data/testsets/orcamentos-aeb-csv.json
git checkout 007-aggregate-rows-enhancements && git stash pop

# with the feature
python -m testset_runner.cli run --testset data/testsets/orcamentos-aeb-csv.json

python -m testset_runner.cli compare data/testset_runs/<baseline>.json data/testset_runs/<feature>.json
```

Use the same `--model` / `--base-url` / `--max-attempts` for both runs. Expected:
- the overall and per-category match rates don't go down,
- questions that need filtered / mean / min-max / distinct / top-N aggregates (listed by id in
  the results note) are matched at least as often,
- the number of answers whose numbers appear in no tool result (checked by hand from the
  retrieval traces, research.md §10) doesn't go up.

Record both run files and the comparison in the feature's results note (Principles I–II).
