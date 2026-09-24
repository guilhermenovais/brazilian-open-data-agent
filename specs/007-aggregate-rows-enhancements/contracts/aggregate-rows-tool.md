# Contract: `aggregate_rows` agent tool (qa_agent wiring)

```python
def aggregate_rows(
    ctx: RunContext[AgentDeps], identifier: str, request: AggregationRequest
) -> AggregationResult | BudgetExhausted: ...
```

This is a thin wrapper in `src/qa_agent/tools.py`, registered by `agent_factory` with
`retries=10`. The signature and the budget/error flow are **unchanged**:

1. Reserve one step. If the budget is spent, return `BudgetExhausted` without calling the capability.
2. Call `data_access.capabilities.aggregate_rows`.
3. Any `DataAccessError` (now including `InvalidSortKeyError`) → `ModelRetry(str(exc))`.
4. On success, record it and return the `AggregationResult` as it is.

A request that fails pydantic validation (`limit < 1`, unknown `function`, a malformed
`order_by` entry) is sent back to the model by pydantic-ai as a retry prompt *before* the
wrapper runs, so it uses no step budget. Both paths are correctable (FR-018).

## Tool description (FR-017)

The wrapper gets a docstring. pydantic-ai 2.45 uses it as the tool description, and its
`Args:` section supplies the parameter descriptions. It MUST cover:

- **Purpose**: group the rows of one data source and compute aggregates per group.
- **Filters apply first**: `request.filters` uses the same conditions as `query_rows`
  (`equals`, `contains`, `range`, combined with AND). Only matching rows are grouped.
- **Functions**: `count` (rows in the group), `sum`, `mean`, `min`, `max` (numeric-like fields
  only; missing values are ignored, and `null` is returned when a group has none),
  `count_distinct` (distinct values that aren't missing, any field).
- **Result keys**: `<function>_<value_field>`, e.g. `sum_valor`. These are the names
  `order_by` accepts, in addition to the `group_by` fields.
- **Ordering**: `order_by` entries are `{key, direction}`, and `direction` defaults to `asc`.
  Use `desc` with `limit` for "top N". Missing values sort last. With no `order_by`, groups
  are sorted ascending by their grouping values.
- **Limit**: optional, ≥ 1, and it counts groups. The result reports `total_group_count` and
  `truncated`.

The new request fields also carry `Field(description=...)` texts, so the JSON schema of the
`request` parameter documents them (data-model.md).

## Tests

A unit test builds the agent (`build_agent` with a test model) and asserts that the registered
`aggregate_rows` tool definition:
- has a description that mentions filtering before aggregation, all six function names,
  and the `<function>_<field>` naming,
- has a parameter schema that includes `filters`, `order_by`, `limit` and the six-value
  `function` enum.

The existing `qa_agent` contract tests that script `aggregate_rows` calls keep passing,
because the new request fields are optional.
