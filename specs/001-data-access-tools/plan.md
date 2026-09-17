# Implementation Plan: Data Access Tool Layer

**Branch**: `001-data-access-tools` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-data-access-tools/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Build the plain-Python, framework-agnostic tool layer an agent uses to explore and query a
dataset of CSV/JSON files: (1) discovery of data sources, (2) schema + sample inspection,
(3) filtered row query (equality/contains/numeric-range), and (4) grouped aggregation
(count/sum). The defining technical challenge is FR-009/FR-010: numeric fields may mix
Brazilian- and US-style formatting within the same field, so every value's locale convention
must be detected and normalized independently rather than assumed per field or per source.
Per Constitution Engineering Principle 1, this feature covers only the plain capability
functions and their pydantic I/O models/typed exceptions — not the `@agent.tool`/
`pydantic-ai` wiring that will call them later (see research.md §1).

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `pydantic` v2 (tool I/O models, Engineering Principle 5), `pandas`
(in-memory `QueryEngine` backend, Engineering Principle 2), Python stdlib `csv`/`json`/`pathlib`
for raw parsing

**Storage**: N/A — read-only local filesystem CSV/JSON files, held in memory per data source
(no database, no persistent write path; tool layer never modifies source files)

**Testing**: pytest — contract tests mirroring spec.md's Acceptance Scenarios 1:1, plus unit
tests for locale-number parsing and dataset identifier/collision logic (research.md §11)

**Target Platform**: Linux server process — library consumed in-process by the agent
codebase (no network service of its own)

**Project Type**: single project (Python library) — this feature has no CLI/UI surface;
`src/` layout, Option 1 from the template

**Performance Goals**: Not specified by the spec beyond "fits in memory" (spec Assumptions);
no explicit throughput/latency target is part of this contract

**Constraints**: Fixed, non-configurable bounded caps (`SAMPLE_SIZE_CAP=20`,
`ROW_QUERY_CAP=100`, research.md §5); read-only; every supported data source assumed to fit
in memory in full (spec Assumptions — oversized sources are a deployment concern, not a
capability requirement)

**Scale/Scope**: 4 capabilities × 2 formats (CSV, JSON) over one bounded dataset per agent
session; no OR/mixed filter logic, no aggregates beyond count/sum (spec Assumptions)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|-----------|------------|
| I. Reproducibility Over One-Off Results | N/A directly — this feature makes no accuracy/comparison claim. Its own correctness is enforced by contract tests (traceable 1:1 to Acceptance Scenarios), which are themselves reproducible. **Pass.** |
| II. Evidence Before Implementation | Every design decision here is driven directly by an FR/Acceptance Scenario/clarification already recorded in spec.md, not speculation; rationale recorded in research.md. **Pass.** |
| III. Documentation Is a Deliverable | Plan produces research.md/data-model.md/contracts/quickstart.md; implementation will need module-level docstrings on `numeric.py`'s parsing rule (non-obvious heuristic) and the `Dataset` abstraction. **Pass**, carried into tasks. |
| IV. Tests Document Behavior | Contract tests named after Acceptance Scenarios (research.md §11); reading `tests/contract/` should read as spec.md's scenarios. **Pass.** |
| V. Separate Mechanism from Domain Knowledge | No dataset-specific field names/schemas are hardcoded anywhere in this design; locale-number detection is generic, not tuned to one dataset. **Pass.** |
| VI. Deterministic Computation Over Model Judgment | All four capabilities, including numeric normalization and aggregation, are pure deterministic code; no model call anywhere in this feature. **Pass**, strongly aligned. |
| VII. Code Quality Is Enforced | Design uses only the abstractions the constitution itself mandates (QueryEngine, DataSourceReader) plus the minimum needed for the spec (no speculative 5th format, no configurable caps not asked for). **Pass.** |
| VIII. Security and Data Stewardship | Read-only, no credentials, no secrets anywhere in this feature. **Pass** (largely N/A). |
| IX. Continuous Integration Gate | pytest + pyright wired into CI is part of this feature's definition of done; tracked as an explicit task in tasks.md. **Pass**, pending task generation. |
| X. Usage as Research Data | Out of scope for this feature — usage/telemetry capture belongs to the (future) agent-orchestration/wiring layer that calls these capabilities, not the capabilities themselves. **N/A**, noted as a dependency for that future feature. |
| Eng. Principle 1 (thin wiring layer) | This feature *is* the plain-Python side of that split; no `pydantic-ai` import anywhere in it (research.md §1). **Pass.** |
| Eng. Principle 2 (interface before 2nd impl) | `QueryEngine` Protocol + `PandasQueryEngine`, `DataSourceReader` Protocol + `CsvReader`/`JsonReader` defined up front (research.md §6–7). **Pass.** |
| Eng. Principle 3 (polymorphic format dispatch) | One reader class per format, selected once in `Dataset`; no scattered `if csv elif json`. **Pass.** |
| Eng. Principle 4 (DI over globals) | `Dataset`/`QueryEngine` are passed as explicit arguments to every capability function, never module globals. **Pass.** |
| Eng. Principle 5 (validated pydantic boundary) | All four capability inputs/outputs are pydantic models (data-model.md); errors are typed exceptions, not untyped dicts. **Pass.** |
| Eng. Principle 6 (tool functions testable without a model) | Capabilities are plain functions taking `Dataset`/model arguments; no `RunContext`/agent needed to call or test them. **Pass.** |
| Eng. Principle 10 (static typing enforced) | pyright in CI (research.md §10), tracked as a task. **Pass**, pending task generation. |

No violations requiring justification. Complexity Tracking table left empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-data-access-tools/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/             # Phase 1 output (/speckit-plan command)
│   ├── discovery.md
│   ├── inspection.md
│   ├── query.md
│   ├── aggregation.md
│   └── errors.md
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
└── data_access/
    ├── __init__.py
    ├── models.py         # pydantic I/O models: DataSourceInfo, DiscoveryResult, FieldInfo,
    │                      # SchemaInspectionResult, FilterCondition variants, RowQueryResult,
    │                      # AggregateSpec, AggregationRequest/Group/Result
    ├── exceptions.py      # DataAccessError and the 5 typed subclasses (contracts/errors.md)
    ├── dataset.py          # Dataset abstraction: folder walk, identifier resolution,
    │                        # collision detection, extension-based non-data-file filtering
    ├── numeric.py           # parse_locale_number() + numeric-like classification threshold
    ├── query_engine.py       # QueryEngine Protocol + PandasQueryEngine
    ├── readers/
    │   ├── __init__.py
    │   ├── base.py           # DataSourceReader Protocol
    │   ├── csv_reader.py      # CsvReader (dtype=str)
    │   └── json_reader.py     # JsonReader (flat array-of-objects, key-union)
    └── capabilities.py         # discover_data_sources, inspect_schema, query_rows,
                                  # aggregate_rows — the 4 public entry points

tests/
├── contract/
│   ├── test_discovery.py       # 1:1 with US1 Acceptance Scenarios
│   ├── test_inspection.py      # 1:1 with US2 Acceptance Scenarios
│   ├── test_query.py           # 1:1 with US3 Acceptance Scenarios
│   └── test_aggregation.py     # 1:1 with US4 Acceptance Scenarios
├── unit/
│   ├── test_numeric.py         # parse_locale_number edge cases (research.md §3)
│   └── test_dataset.py         # identifier derivation, collision detection, non-data filtering
└── fixtures/
    └── sample_dataset/          # CSV/JSON fixtures incl. nested folders, mixed-locale
                                  # numbers, a malformed CSV, and a non-data file
```

**Structure Decision**: Single-project library layout (Option 1 from the template, adapted
with domain-specific directory names in place of the generic `models/services/cli/lib`
placeholders). This feature has no CLI or web surface — the deliverable is a Python package
(`src/data_access/`) consumed in-process by a future agent-wiring feature, per Constitution
Engineering Principle 1's split between business logic and orchestration.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations recorded — table intentionally left empty.
