"""Thin @agent.tool wrappers over data_access.capabilities (contracts/tools.md).

Each wrapper: (1) reserves one unit of the step budget, returning `BudgetExhausted`
without calling the underlying capability if the budget is already spent (FR-012);
(2) calls the matching data_access.capabilities function; (3) on success, records
the success and returns the capability's result model as-is; (4) on any
DataAccessError, raises pydantic_ai.ModelRetry so the model can self-correct
(research.md §4) — registered with retries=10 by agent_factory so pydantic-ai's own
retry ceiling never terminates a run before StepBudget does.
"""

from pydantic_ai import ModelRetry, RunContext

from data_access import capabilities as data_access
from data_access.exceptions import DataAccessError
from data_access.models import (
    AggregationRequest,
    AggregationResult,
    DiscoveryResult,
    FilterCondition,
    RowQueryResult,
    SchemaInspectionResult,
)
from qa_agent.deps import AgentDeps
from qa_agent.step_budget import BudgetExhausted


def discover_data_sources(
    ctx: RunContext[AgentDeps],
) -> DiscoveryResult | BudgetExhausted:
    if not ctx.deps.step_budget.try_reserve():
        return BudgetExhausted()
    try:
        result = data_access.discover_data_sources(ctx.deps.dataset)
    except DataAccessError as exc:
        raise ModelRetry(str(exc)) from exc
    ctx.deps.step_budget.record_success()
    return result


def inspect_schema(
    ctx: RunContext[AgentDeps], identifier: str
) -> SchemaInspectionResult | BudgetExhausted:
    if not ctx.deps.step_budget.try_reserve():
        return BudgetExhausted()
    try:
        result = data_access.inspect_schema(ctx.deps.dataset, identifier)
    except DataAccessError as exc:
        raise ModelRetry(str(exc)) from exc
    ctx.deps.step_budget.record_success()
    return result


def query_rows(
    ctx: RunContext[AgentDeps], identifier: str, filters: list[FilterCondition]
) -> RowQueryResult | BudgetExhausted:
    if not ctx.deps.step_budget.try_reserve():
        return BudgetExhausted()
    try:
        result = data_access.query_rows(ctx.deps.dataset, identifier, filters)
    except DataAccessError as exc:
        raise ModelRetry(str(exc)) from exc
    ctx.deps.step_budget.record_success()
    return result


def aggregate_rows(
    ctx: RunContext[AgentDeps], identifier: str, request: AggregationRequest
) -> AggregationResult | BudgetExhausted:
    """Group the rows of one data source and compute aggregates for each group.

    Filters apply first: `request.filters` takes the same conditions as `query_rows`
    (`equals`, `contains`, `range`), combined with AND, and only matching rows are
    grouped and aggregated, i.e. filters are applied before grouping.

    Functions: `count` (rows in the group, any field); `sum`, `mean`, `min`, `max`
    (numeric-like fields only; missing or unparseable values are ignored, and
    `mean`/`min`/`max` are `null` when a group has no usable value, `sum` is 0);
    `count_distinct` (number of distinct non-missing values, any field).

    Each result is stored under the key `<function>_<value_field>`, e.g. `sum_valor`.
    `order_by` accepts these result keys and the `group_by` fields; if a name is both,
    it refers to the grouping field.

    Ordering: `order_by` is a list of `{key, direction}` entries, where `direction`
    is `asc` (default) or `desc`; later entries break ties. Missing values always
    sort last. Without `order_by`, groups are sorted ascending by their grouping
    values. For "top N" questions use `order_by` with `desc` plus `limit`.

    Limit: optional, at least 1, and counts groups (applied after ordering). The
    result reports `total_group_count` (groups before the limit) and `truncated`.

    Args:
        identifier: The data source identifier, as returned by discover_data_sources.
        request: What to group by, which aggregates to compute, and optional
            filters, order_by and limit.
    """
    if not ctx.deps.step_budget.try_reserve():
        return BudgetExhausted()
    try:
        result = data_access.aggregate_rows(ctx.deps.dataset, identifier, request)
    except DataAccessError as exc:
        raise ModelRetry(str(exc)) from exc
    ctx.deps.step_budget.record_success()
    return result
