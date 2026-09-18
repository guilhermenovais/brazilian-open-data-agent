# Contract: The Agent's Tools

Four `@agent.tool` functions, registered on the `Agent[AgentDeps, AgentAnswer]` built by
`agent_factory.build_agent`. Each is a thin adapter (Engineering Principle 1) over the
matching `data_access.capabilities` function, unchanged from `001-data-access-tools`'s own
contracts (`discovery.md`, `inspection.md`, `query.md`, `aggregation.md`) — this file
documents only what the wrapper adds: step-budget enforcement and error translation.

```python
@agent.tool
def discover_data_sources(ctx: RunContext[AgentDeps]) -> DiscoveryResult | BudgetExhausted: ...

@agent.tool
def inspect_schema(ctx: RunContext[AgentDeps], identifier: str) -> SchemaInspectionResult | BudgetExhausted: ...

@agent.tool
def query_rows(
    ctx: RunContext[AgentDeps], identifier: str, filters: list[FilterCondition]
) -> RowQueryResult | BudgetExhausted: ...

@agent.tool
def aggregate_rows(
    ctx: RunContext[AgentDeps], identifier: str, request: AggregationRequest
) -> AggregationResult | BudgetExhausted: ...
```

Every input/output type above (`DiscoveryResult`, `SchemaInspectionResult`, `FilterCondition`,
`AggregationRequest`, `AggregationResult`, ...) is exactly the `001-data-access-tools` model
of the same name — no parallel "agent-facing" schema is defined (data-model.md, "Reused
types").

## Shared wrapper behavior (all four tools)

Each call, in order:

1. `ctx.deps.step_budget.try_reserve()`. If it returns `False` (limit already reached), the
   wrapper returns `BudgetExhausted(message=...)` immediately — the underlying
   `data_access.capabilities` function is **not** called (FR-012, research.md §3). This does
   not raise; it's an ordinary tool result the model sees like any other.
2. Otherwise, call the matching `data_access.capabilities` function against
   `ctx.deps.dataset`.
3. On success: `ctx.deps.step_budget.record_success()`, return the capability's result model
   as-is.
4. On `data_access.exceptions.DataAccessError` (any subclass): raise `pydantic_ai.ModelRetry`
   with a message naming the problem (research.md §4) — this is internal model context, not
   shown to the end user; the system prompt (`prompts/system_v1.md`) instructs the model to
   never repeat such detail in its final `answer`.

Each tool is registered with `retries=10` (research.md §3) so `pydantic-ai`'s own per-tool
retry ceiling is never the thing that stops a run before `StepBudget` does.

## Behavioral requirements (traceability)

| Scenario / Requirement | Behavior |
|-------------------------|----------|
| US3 AS3 (inspect before filter) | Nothing prevents the model from calling `inspect_schema` before `query_rows`/`aggregate_rows` within the same 10-step budget — both consume from the same counter. |
| FR-004 | Every fact in the final answer is traceable to one of these four tool calls having actually run during this request — no fifth, uncounted way to read data exists. |
| FR-008 | The model chooses the sequence (discover → inspect → query/aggregate) itself; the wrapper imposes no fixed order, only the total-count bound. |
| FR-012 | The 11th attempted call of any of these four tools in one request returns `BudgetExhausted` instead of executing; the 10th and earlier execute normally (data-model.md, `StepBudget`). |
| `001` FieldNotFoundError/NumericTypeError/UnreadableSourceError/DataSourceNotFoundError/IdentifierCollisionError | Each becomes a `ModelRetry` (still consumes one budget unit) rather than crashing the run — see `errors.md`. |
