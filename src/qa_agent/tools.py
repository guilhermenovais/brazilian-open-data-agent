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
    if not ctx.deps.step_budget.try_reserve():
        return BudgetExhausted()
    try:
        result = data_access.aggregate_rows(ctx.deps.dataset, identifier, request)
    except DataAccessError as exc:
        raise ModelRetry(str(exc)) from exc
    ctx.deps.step_budget.record_success()
    return result
