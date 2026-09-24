# Implementation Plan: Richer Aggregation (Filters, Functions, Ordering, Limit)

**Branch**: `007-aggregate-rows-enhancements` | **Date**: 2026-09-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-aggregate-rows-enhancements/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

`aggregate_rows` gets three additions, all optional, so existing requests keep working:

1. **Filters.** `AggregationRequest.filters` reuses `FilterCondition` (`equals`, `contains`,
   `range`, AND). The engine applies them before grouping by reusing its own `query_rows`
   mask, and the capability validates them with the existing `_validate_filter_fields`.
   Filter semantics therefore can't drift from row queries (research.md §1, §3).
2. **Functions.** `mean`, `min`, `max` (numeric-like only, missing values ignored, `None` for
   a group with no usable value) and `count_distinct` (any field, exact values, missing
   values excluded). Numeric-like classification always uses the **unfiltered** source and the
   `inspect_schema` rule, now in one helper (research.md §2, §4, §5).
3. **Order and limit.** `order_by: list[SortKey]` over grouping fields or `<function>_<field>`
   result keys, with missing values last in both directions. Groups are always put in a
   deterministic default order (ascending by grouping values). `limit ≥ 1` is applied last, and
   the result reports `total_group_count` and `truncated` (research.md §6–§8).

A new `InvalidSortKeyError(DataAccessError)` reaches the agent through the existing
`ModelRetry` path. The `qa_agent.tools.aggregate_rows` wrapper gets a docstring, which
pydantic-ai turns into the tool description the agent sees (research.md §9).

## Technical Context

**Language/Version**: Python 3.11+ (venv currently 3.12)

**Primary Dependencies**: `pandas` ≥ 2 (existing engine), `pydantic` v2, `pydantic-ai` 2.45.0
(tool description from the docstring, verified in the venv). No new dependency.

**Storage**: N/A. Sources are read-only CSV/JSON. Aggregation results are never persisted as
models (`RetrievalStep` keeps only a summary string), so the result-shape change needs no
migration.

**Testing**: pytest + pyright (existing CI: `pytest tests/contract tests/unit`, `pyright src/`).
Contract tests extend `tests/contract/data_access/test_aggregation.py` with a hand-computed
fixture. New unit tests cover engine ordering and the tool description.

**Target Platform**: Linux, local Python process (library + CLI/web UI).

**Project Type**: Single-project Python library (`src/` layout).

**Performance Goals**: Nothing beyond staying linear in rows. Numeric fields are parsed once
per request instead of once per group (research.md §5). Group ordering is in-memory over at
most one entry per distinct group combination (~5,570 for municipalities).

**Constraints**: FR-016/SC-001: same groups and values for pre-feature requests, with only
the order changing. `data_access` keeps no `pydantic-ai` import (FR-019). Ordering is
deterministic and doesn't depend on the host locale (research.md §7).

**Scale/Scope**: Edits to four `data_access` modules (`models`, `exceptions`, `query_engine`,
`capabilities`) and one `qa_agent` module (`tools`: docstring only). A new fixture, extended
contract tests and two new unit-test files. No change to `dataset_selector`,
`testset_runner` or `web_ui`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|-----------|------------|
| I. Reproducibility | Group order is fully deterministic: the default order doesn't depend on source row order, and code-point text ordering doesn't depend on the host's locale (research.md §7). SC-004 is measured with recorded before/after testset runs and `compare` (research.md §10, quickstart §4). **Pass.** |
| II. Evidence Before Implementation | Motivated by a documented gap: scoped/averaged/extreme/distinct/top-N questions can't be answered with one mechanical call today, so the agent falls back to its own arithmetic (spec intro, Principle VI). The effect is measured with SC-004 runs whose results are kept in a results note. **Pass**, and the results note is carried into tasks. |
| III. Documentation Is a Deliverable | research.md, data-model.md, contracts and quickstart are produced. The `001` aggregation contract is superseded by `contracts/aggregation.md` here. Module/function docstrings are updated (`query_engine`, `capabilities`, tool docstring). **Pass**, carried into tasks. |
| IV. Tests Document Behavior | One contract test per acceptance scenario, named `test_007_us<N>_<M>_...`, following the `001` naming. Hand-computed expected literals (SC-002). The ordering unit tests state each rule in their names. **Pass.** |
| V. Mechanism vs Domain Knowledge | Nothing dataset-specific. Field names come from requests, and numeric classification is the generic sampling rule. **Pass.** |
| VI. Deterministic Over Model Judgment | This is the purpose of the feature: filtering, averages, extremes, distinct counts and top-N move from model arithmetic into mechanical computation. **Pass.** |
| VII. Code Quality / Simplicity | No new Protocol and no new dependency. One new exception type. The existing classification rule is deduplicated into one helper instead of a fourth inline copy. No `groupby().agg` rewrite and no default limit (research.md §5, §8). **Pass.** |
| VIII. Security & Data Stewardship | No credentials, network or storage involved. **Pass (N/A).** |
| IX. CI Gate | The existing pytest + pyright CI covers all touched modules and the new tests. **Pass.** |
| X. Usage as Research Data | Tool arguments (including the new filters/order/limit) are already captured in `RetrievalStep.arguments` in the run log, so no extra work is needed. **Pass.** |
| Eng. 1 (thin wiring) | All logic stays in `data_access`. `qa_agent.tools` only gains a docstring. **Pass.** |
| Eng. 2 (interface before 2nd impl) | The existing `QueryEngine` protocol is extended (`aggregate(..., numeric_group_fields)`), so a future `DuckDBQueryEngine` can push down filter/group/order. **Pass.** |
| Eng. 3 (polymorphic dispatch) | N/A. The per-function computation is a small table inside one engine, not format/backend dispatch. |
| Eng. 4 (DI over globals) | Unchanged. The dataset comes in through `RunContext[AgentDeps]`. The module-level `_ENGINE` is a pre-existing stateless instance, left as it is. **Pass.** |
| Eng. 5 (validated boundary) | `SortKey`, `limit ≥ 1` and the function `Literal` are pydantic-validated at the tool boundary. **Pass.** |
| Eng. 6 (testable without a model) | Every new behavior is tested by calling `data_access.capabilities.aggregate_rows` directly. **Pass.** |
| Eng. 7 (typed settings) | No new settings. **N/A.** |
| Eng. 8 (versioned prompts/tool schemas) | `system_v1.md` is not edited (research.md §9). The tool schema/description changes are in code and versioned in git. Runs are compared across commits (quickstart §4). **Pass.** |
| Eng. 9 (native instrumentation) | Unchanged. **Pass.** |
| Eng. 10 (static typing) | Full hints. `results` values are widened to `float \| int \| None`. pyright runs in CI. **Pass.** |

**Post-design re-check (after Phase 1)**: still **Pass** on all rows. The only interface
change is the extra `numeric_group_fields` parameter on `QueryEngine.aggregate`, which the
unfiltered-classification requirement (Clarification 3) makes necessary. The only new public
type besides the models is `InvalidSortKeyError`, which fits the existing `DataAccessError`
family.

## Project Structure

### Documentation (this feature)

```text
specs/007-aggregate-rows-enhancements/
├── plan.md                          # This file
├── research.md                      # Phase 0
├── data-model.md                    # Phase 1
├── quickstart.md                    # Phase 1
├── contracts/
│   ├── aggregation.md               # data_access.capabilities.aggregate_rows (supersedes 001's)
│   └── aggregate-rows-tool.md       # qa_agent tool wrapper + description (FR-017/018)
├── checklists/requirements.md       # from /speckit-specify
└── tasks.md                         # Phase 2 (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
src/
├── data_access/
│   ├── models.py            # AggregateFunction; SortKey (new); AggregationRequest.filters/order_by/limit;
│   │                        #   AggregationGroup.results allows None; AggregationResult.total_group_count/truncated
│   ├── exceptions.py        # + InvalidSortKeyError
│   ├── query_engine.py      # aggregate(df, request, numeric_group_fields): filter → group → aggregate → order
│   └── capabilities.py      # _is_numeric_field helper; validation order (research §3); limit + counts
└── qa_agent/
    └── tools.py             # aggregate_rows docstring = agent-facing tool description

tests/
├── contract/data_access/test_aggregation.py        # + 007 US1–US3 and edge cases; existing cases unchanged
├── unit/data_access/test_query_engine.py           # NEW: ordering rules, determinism
├── unit/qa_agent/test_tools_description.py         # NEW: tool description/schema (FR-017)
└── fixtures/data_access/sample_dataset/
    └── <new aggregation fixture>.csv               # NEW: years, text + numeric-like groups, BR numbers, missing cells
```

**Structure Decision**: The same single-project layout as `001`–`006`. The change is limited to
`data_access` (logic) plus a docstring in the `qa_agent` wiring layer. Adding a fixture file
under `sample_dataset/` is safe, because the discovery tests look up sources by identifier
rather than asserting an exact list.

## Complexity Tracking

No violations. Table intentionally left empty.
