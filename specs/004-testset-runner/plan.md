# Implementation Plan: Testset Runner for LLM Evaluation

**Branch**: `004-testset-runner` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-testset-runner/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See
`.specify/templates/plan-template.md` for the execution workflow.

## Summary

Build a new `testset_runner` package that drives the existing `qa_agent.answer_question`
capability once per question over a fixed testset (starting with the bundled 50-question
`data/testsets/orcamentos-aeb-csv.json`), deterministically grades numeric answers, routes
everything else to human review, and persists the full per-question detail (answer, agent
outcome, dataset selected, retrieval-step trace, match status) plus a run summary as one JSON
file per run — so a run can be started against any model/URL without touching source code, and
two persisted runs of the same testset can be compared to see exactly which questions changed.
Per-question isolation is inherited directly from `qa_agent`'s existing per-call
`Agent`/`AgentDeps` construction; this feature does not need to build isolation itself. Two
small, additive extensions to `qa_agent`'s existing public contract are required to make this
possible: exposing the tool-call trace and a genuine `errored` signal on
`QuestionAnsweringResult`, and letting `AgentSettings` carry an optional custom `base_url` so a
run can target a self-hosted or alternate-provider endpoint as pure configuration.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `qa_agent.capabilities.answer_question` (reused as the sole path to a
real model answer — this feature adds no second path into `pydantic-ai`); `pydantic-ai`'s
`OpenAIChatModel`/`OpenAIProvider` (for the custom-`base_url` target-configuration case,
research.md §4); `pydantic` v2 (all new boundary-crossing models, Engineering Principle 5);
`data_access.numeric.parse_locale_number` (reused unmodified for numeric match-grading,
research.md §5); no new third-party dependency is introduced.

**Storage**: One new write path — one JSON file per completed run at
`data/testset_runs/<run_id>.json` (research.md §7), gitignored the same way as the existing
`data/logs/`. Reads: the bundled (and any future) testset JSON file(s) under `data/testsets/`
(already present, untracked pending this feature — no schema change needed), and, for
`compare_runs`, two previously saved run files. No database.

**Testing**: pytest — contract tests mirroring spec.md's Acceptance Scenarios 1:1 (quickstart.md
Scenarios 1–7), driven by a hand-written fake `QuestionAnswerer` for all `testset_runner`-owned
logic (loading, matching, persisting, comparing — no model, no network), plus one additional
`qa_agent` contract test using `pydantic_ai.models.function.FunctionModel` to prove the new
`steps`/`errored` extraction logic against a real (scripted) agent run (research.md §10).
Model-quality claims are out of scope for this feature's own report accuracy — the CLI's
live-model track (quickstart.md) is how a person actually judges a real model's performance
using this tool, which is the feature's whole point, not a Success Criterion this plan itself
proves with a scripted double.

**Target Platform**: Linux server process — a CLI (`python -m testset_runner.cli`) plus the
underlying library functions (`run_testset`, `compare_runs`) usable in-process by any future
caller; no network service of its own beyond `qa_agent`'s existing outbound model-provider call.

**Project Type**: single project (Python library + CLI) — `src/` layout, Option 1 from the
template, adding a sibling `testset_runner` package alongside `data_access`/`dataset_selector`/
`qa_agent`, plus small additive changes to `qa_agent` itself.

**Performance Goals**: Not specified beyond completing a 50-question run sequentially in one
process invocation (spec Assumptions: "tens to low hundreds of questions... a run completing
fully before a person reviews it is an acceptable way of working"); no latency/throughput target.

**Constraints**: Every question in a run is answered in isolation, with zero state carried from
one question to the next (FR-003, SC-004); a run either produces a complete report for every
question or fails before starting, never a partial one presented as complete (FR-013, Edge
Cases); no credential is ever persisted in a run file (Constitution Principle VIII); automatic
match grading only ever applies to numeric expected values — everything else is flagged for
human review, never silently guessed (FR-006/FR-007).

**Scale/Scope**: 2 public capabilities (`run_testset`, `compare_runs`) plus a CLI wrapping both;
one run drives up to "low hundreds" of sequential `answer_question` calls; comparison operates
over exactly two persisted runs at a time (spec Assumptions: no multi-user/concurrency/CI
integration scope).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|-----------|------------|
| I. Reproducibility Over One-Off Results | Every run is a persisted, self-describing artifact (testset content hash, target configuration, full per-question detail) — exactly the "pipeline that can be re-run and re-verified, with inputs, outputs, and run conditions recorded" this principle requires. Comparing two runs is itself only possible because both are reproducible records, not ad hoc notes. **Pass.** |
| II. Evidence Before Implementation | Every research.md decision cites a specific FR/Acceptance Scenario/Assumption/Edge Case already in spec.md; the match-grading rule (research.md §5) was specifically checked against the bundled testset's own actual non-numeric values before being finalized, not designed in the abstract. **Pass.** |
| III. Documentation Is a Deliverable | This plan produces research.md/data-model.md/contracts/quickstart.md; the `MatchStrategy`/`QuestionAnswerer` seams and the additive `qa_agent` contract changes are documented at the module level, carried into tasks. **Pass**, carried into tasks. |
| IV. Tests Document Behavior | Contract tests are named after and map 1:1 to spec.md's Acceptance Scenarios (quickstart.md); the one `FunctionModel`-driven test for the new `qa_agent` extraction logic exists specifically because Principle IV requires new behavior to be demonstrated, not assumed (research.md §10). **Pass.** |
| V. Separate Mechanism from Domain Knowledge | `testset_runner`'s core (loading, matching, comparing, persisting) contains no fact specific to the AEB budget dataset; the bundled testset is just a data file it happens to be validated against. The "target unreachable" heuristic and match-grading rule are deliberately kept dataset/testset-content-agnostic (research.md §5/§6) rather than keyed on this testset's own category labels. **Pass.** |
| VI. Deterministic Computation Over Model Judgment | Match grading, run-level unreachable-target detection, and comparison transitions are all pure deterministic code — no model is ever asked "did this answer match?" (research.md §5, directly enforcing FR-006/FR-007). **Pass.** |
| VII. Code Quality Is Enforced | The two new Protocol seams (`QuestionAnswerer`, `MatchStrategy`) are each justified by a named spec axis that already varies (research.md §1/§5), not speculative generality; the `base_url` extension exercises, rather than duplicates, `pydantic-ai`'s own already-accepted provider abstraction (research.md §4). **Pass.** |
| VIII. Security and Data Stewardship | `TargetConfiguration`/persisted `TestRun` files never contain an API key (data-model.md); `AgentSettings.api_key` is read from an env var at runtime, same as `003`'s existing reliance on provider SDK env vars, and used only in-process to construct a `Provider`, never logged or written to disk. **Pass.** |
| IX. Continuous Integration Gate | pytest + pyright wired into CI is part of this feature's definition of done, same as `001`/`002`/`003`; tracked as a task. **Pass**, pending task generation. |
| X. Usage as Research Data | This feature *is*, in effect, a structured research-data product: every run is a persisted, comparable record of the agent's real behavior against a known-answer question set — directly extending Principle X beyond the per-question `AgentRunLogEntry` `003` already writes. **Pass.** |
| Eng. Principle 1 (thin wiring layer) | `testset_runner` never imports `pydantic_ai` directly for answering questions — it calls `qa_agent.answer_question` through the `QuestionAnswerer` seam; only the small `qa_agent.agent_factory`/`capabilities` extensions (already `pydantic-ai`-importing files in `003`) touch the framework for the new `base_url`/`steps` work (research.md §1/§3/§4). **Pass.** |
| Eng. Principle 2 (interface before 2nd impl) | `QuestionAnswerer` and `MatchStrategy` are both defined now, each with exactly one concrete implementation, because each corresponds to an axis the spec itself already names as varying (fake vs. real answerer for testing; numeric vs. everything-else grading) — not spec-free speculation. **Pass.** |
| Eng. Principle 3 (polymorphic format dispatch) | N/A — testset files are a single fixed JSON schema in this feature; no format-dispatch concern. |
| Eng. Principle 4 (DI over globals) | `run_testset`/`compare_runs` take `answerer`, `matcher`, and `store` as explicit parameters; no module-level global run state. **Pass.** |
| Eng. Principle 5 (validated pydantic boundary) | `Testset`, `Question`, `TargetConfiguration`, `TestRun`, `QuestionResult`, `RunSummary`, `RunComparison`, `ComparisonEntry`, and the new `qa_agent.RetrievalStep` are all pydantic models (data-model.md); no untyped dict crosses any of these boundaries. **Pass.** |
| Eng. Principle 6 (tool functions testable without a model) | `TestsetLoader`, `DeterministicMatcher`, `RunStore`, and `compare_runs`'s transition logic are all unit-tested with a fake `QuestionAnswerer` and zero `pydantic-ai` involvement (research.md §10). **Pass.** |
| Eng. Principle 7 (typed centralized settings) | `AgentSettings` remains the one typed settings object governing how any `Agent` is built, extended (not duplicated) with `base_url`/`api_key`; `TargetConfiguration` is the run-level record of the model-relevant *subset* of that settings object worth persisting (data-model.md). **Pass.** |
| Eng. Principle 8 (prompts/briefings versioned) | Unaffected — this feature reuses `003`'s existing prompt/briefing wiring unchanged; no new prompt content is introduced. **Pass** (N/A change). |
| Eng. Principle 9 (native instrumentation preferred) | Unaffected — `Agent(instrument=...)` wiring is unchanged; this feature's own run/comparison records remain the bespoke, structured research artifact appropriate for FR-008/FR-009/FR-010 (mirrors `003`'s research.md §8 reasoning that tracing spans and a structured per-run record serve different purposes). **Pass.** |
| Eng. Principle 10 (static typing enforced) | pyright in CI (research.md §11), tracked as a task. **Pass**, pending task generation. |

No violations requiring justification. Complexity Tracking table left empty.

## Project Structure

### Documentation (this feature)

```text
specs/004-testset-runner/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── running.md
│   ├── comparing.md
│   └── errors.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── qa_agent/                          # 003, extended additively by this feature
│   ├── models.py                        # + RetrievalStep; QuestionAnsweringResult + steps/errored fields
│   ├── settings.py                       # AgentSettings + base_url, api_key fields
│   ├── agent_factory.py                   # build_agent: constructs OpenAIChatModel+OpenAIProvider when base_url is set
│   └── capabilities.py                     # populates steps from run_result.all_messages(); sets errored=True on both failure paths
│
└── testset_runner/                    # new package
    ├── __init__.py
    ├── models.py                         # Question, Testset, TargetConfiguration, QuestionResult, RunSummary, TestRun, ComparisonEntry, RunComparison
    ├── loader.py                          # TestsetLoader.load(path) -> Testset (validates, computes content_hash)
    ├── matcher.py                          # MatchStrategy Protocol, NumericMatchStrategy, DeterministicMatcher
    ├── question_answerer.py                 # QuestionAnswerer Protocol + QaAgentQuestionAnswerer adapter over qa_agent.answer_question
    ├── runner.py                             # run_testset(...) -> TestRun (contracts/running.md)
    ├── store.py                               # RunStore Protocol + JsonFileRunStore (save/load one TestRun per file)
    ├── comparator.py                           # compare_runs(...) -> RunComparison (contracts/comparing.md)
    ├── exceptions.py                            # TestsetRunnerError, TestsetLoadError, RunLoadError, IncompatibleRunsError
    └── cli.py                                    # argparse `run`/`compare` subcommands (research.md §9)

tests/
├── contract/
│   ├── qa_agent/
│   │   └── test_retrieval_trace.py       # NEW — FunctionModel-driven: steps/errored fields (research.md §3/§10)
│   └── testset_runner/
│       ├── test_run_testset.py            # 1:1 with US1 Acceptance Scenarios (fake QuestionAnswerer)
│       ├── test_compare_runs.py            # 1:1 with US2 Acceptance Scenarios
│       └── test_errors.py                   # TestsetLoadError / RunLoadError / IncompatibleRunsError paths
├── unit/
│   └── testset_runner/
│       ├── test_loader.py                    # schema validation, content_hash, duplicate-n rejection
│       ├── test_matcher.py                    # numeric normalization, ~tolerance, non-numeric → needs_review
│       ├── test_store.py                       # JsonFileRunStore save/load round-trip, one-file-per-run
│       └── test_comparator.py                   # transition-bucket logic, hash-gating
└── fixtures/
    └── testset_runner/
        ├── mini-testset.json                     # small, fast fixture for loader/runner tests
        ├── missing-expected-field.json             # FR-013 fail-fast fixture
        └── duplicate-n.json                         # duplicate-identifier fail-fast fixture

data/
└── testset_runs/                              # new, gitignored like data/logs/ — one JSON file per completed run
```

**Structure Decision**: Single-project library + CLI layout, consistent with `001`–`003`
(`src/<package>/`, `tests/{contract,unit}/<package>/`, `tests/fixtures/<package>/`). This
feature adds one new sibling package (`testset_runner`) and makes small, additive,
backward-compatible changes to the existing `qa_agent` package (no changes to `data_access` or
`dataset_selector`). `run_testset`/`compare_runs` are the only two public entry points a future
CLI/API layer beyond this feature's own `cli.py` would call.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations recorded — table intentionally left empty.
