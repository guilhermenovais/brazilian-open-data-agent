# Implementation Plan: Question-Answering Agent Workflow

**Branch**: `003-qa-agent-workflow` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-qa-agent-workflow/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See
`.specify/templates/plan-template.md` for the execution workflow.

## Summary

Build the orchestration layer that turns a Portuguese natural-language question into a
grounded Portuguese answer: deterministically select the dataset via the existing
`dataset_selector.select_dataset` capability (FR-002), then run a `pydantic-ai` `Agent`
whose tools are thin wrappers over the existing `data_access.capabilities` functions
(discovery, schema inspection, filtered query, aggregation), bounded to at most 10
retrieval-tool invocations (FR-012), producing a structured `AgentAnswer` (Portuguese answer
text + a full/partial/none outcome) that a public `answer_question(...)` capability logs and
returns. This is the first feature in the codebase that actually imports `pydantic-ai` —
`001-data-access-tools` and `002-dataset-selector` both explicitly deferred that wiring
(their research.md §1) — so this plan's central technical decisions are about *how* that
wiring stays thin (Engineering Principle 1): the step bound, error translation, and outcome
determination are done with plain deterministic code around the `Agent`, not inside it, and
the two dependency modules are reused exactly as they behave today, unmodified.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `pydantic-ai` (the `Agent`, tool registration, `RunContext[Deps]`,
`ModelRetry` — the first feature to introduce this dependency); `pydantic` v2 (I/O models,
Engineering Principle 5); `pydantic-settings` (`AgentSettings` — the first typed settings
object in this codebase, Engineering Principle 7); the existing `data_access` package
(all four capabilities plus their models/exceptions, reused as-is) and `dataset_selector`
package (`select_dataset`, reused as-is, called once per question before any tool call)

**Storage**: N/A for reads (no database) — same read-only `data/briefings/` and
`data/datasets/` as `002-dataset-selector`. One new write path: an append-only JSONL agent
run log (FR-013), same pattern as `002-dataset-selector`'s selection log, default path
`data/logs/qa_agent_runs.jsonl` (already covered by the existing `data/logs/` `.gitignore`
entry — no `.gitignore` change needed).

**Testing**: pytest — contract tests mirroring spec.md's Acceptance Scenarios 1:1, driven by
`pydantic_ai.models.test.TestModel`/`pydantic_ai.models.function.FunctionModel` so the
deterministic wiring (step-bound enforcement, error translation, dataset-selection-failure
handling, outcome clamping) is fully testable with zero network calls and no API key
(research.md §10). Accuracy/no-fabrication Success Criteria (SC-001/SC-002/SC-005) are
inherently model-quality properties that cannot be asserted by a scripted test double;
research.md §10 documents a separate, reproducible live-model evaluation harness for those
(Constitution Principle I), run out-of-band from the pytest/CI gate.

**Target Platform**: Linux server process — library consumed in-process by whatever future
surface calls `answer_question` (CLI/API); no network service of its own beyond the
outbound call to whichever model provider `AgentSettings.model_name` names.

**Project Type**: single project (Python library) — `src/` layout, Option 1 from the
template, adding a sibling `qa_agent` package alongside `data_access`/`dataset_selector`.

**Performance Goals**: Not specified by the spec beyond the fixed 10-retrieval-step bound
(FR-012); no latency/throughput target is part of this contract.

**Constraints**: At most 10 retrieval-tool invocations per question (FR-012, fixed, not
caller-configurable — spec Assumptions); every question is a fully independent request with
no carried-over state (FR-011); the final answer is Portuguese-only regardless of the
dataset's own field-name language (FR-001/FR-003); no factual content in the final answer
may be untraceable to a retrieval performed during that same request (FR-005).

**Scale/Scope**: 1 public capability (`answer_question`) orchestrating 1 dataset-selection
call + up to 4 distinct retrieval tool types (≤10 total invocations) + 1 structured-output
model call per question; no multi-turn/conversation state (spec Assumptions).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|-----------|------------|
| I. Reproducibility Over One-Off Results | The deterministic wiring (step bound, error translation, outcome clamping, logging) is covered by reproducible `TestModel`/`FunctionModel` contract tests. The model-quality Success Criteria (SC-001/002/005) are explicitly *not* claimed as passing from this plan alone — research.md §10 requires a reproducible, recorded evaluation run (fixed question set + recorded `AgentSettings` + recorded outputs) before any accuracy claim is made. **Pass**, with the evaluation-harness follow-on tracked explicitly rather than assumed. |
| II. Evidence Before Implementation | Every design decision (deterministic pre-step selection, bespoke step budget, `ModelRetry` translation, outcome clamp) is justified by a specific FR/Acceptance Scenario/Assumption already in spec.md, cited in research.md. **Pass.** |
| III. Documentation Is a Deliverable | This plan produces research.md/data-model.md/contracts/quickstart.md; the system prompt template and the non-obvious outcome-clamp rule need module/file-level documentation carried into tasks. **Pass**, carried into tasks. |
| IV. Tests Document Behavior | Contract tests named after Acceptance Scenarios per user story (research.md §10/quickstart.md), using `FunctionModel` to script exactly the tool-call sequence each scenario describes. **Pass.** |
| V. Separate Mechanism from Domain Knowledge | No dataset-specific field names or facts appear in `qa_agent`'s code; the briefing text (already externalized in `data/briefings/`) is the only source of dataset-specific content, injected at render time into the system prompt. **Pass.** |
| VI. Deterministic Computation Over Model Judgment | Dataset selection, the 10-step bound, and the zero-retrievals-forces-"none" outcome clamp are all deterministic code, not model judgment (research.md §2/§3/§5). Model judgment is reserved for what genuinely requires it: interpreting the question, resolving field-name ambiguity (FR-010), and classifying full-vs-partial once at least one retrieval has occurred. **Pass**, deliberately balanced per research.md §5. |
| VII. Code Quality Is Enforced | Every abstraction introduced (`StepBudget`, `AgentSettings`, the tool wrappers) is directly motivated by a cited FR or Engineering Principle, not spec-free speculation; no bespoke `ModelProvider` abstraction is added on top of `pydantic-ai`'s own model-string configuration (research.md §6) since that would be unused generality. **Pass.** |
| VIII. Security and Data Stewardship | No credentials in the working tree; the model provider's API key is read from the provider's own standard environment variable (e.g. `OPENAI_API_KEY`) by `pydantic-ai`/the underlying SDK, never handled or logged by this feature's code. **Pass.** |
| IX. Continuous Integration Gate | pytest + pyright wired into CI is part of this feature's definition of done, same as `001`/`002`; tracked as a task. **Pass**, pending task generation. |
| X. Usage as Research Data | Directly in scope via FR-013 — `AgentRunLogEntry`/`JsonlRunLogger` (research.md §9) mirrors `002-dataset-selector`'s already-established `usage_log.py` pattern exactly. **Pass.** |
| Eng. Principle 1 (thin wiring layer) | This feature *is* the wiring layer, by definition — but it stays thin: all business logic (data access, selection) is reused unmodified from `001`/`002`; the only new logic here is orchestration, the step budget, and error translation, all plain Python outside the one `tools.py`/`agent_factory.py` pair that actually imports `pydantic_ai` (research.md §1). **Pass.** |
| Eng. Principle 2 (interface before 2nd impl) | `RunLogger` `Protocol` defined now (mirrors `SelectionLogger`, same justification: FR-013 plus the near-certain future need to swap in native tracing-backed logging). Model provider swapping is delegated to `pydantic-ai`'s own already-Protocol-shaped model configuration (research.md §6) rather than a redundant second abstraction. **Pass.** |
| Eng. Principle 3 (polymorphic format dispatch) | N/A — no file-format dispatch concern in this feature. |
| Eng. Principle 4 (DI over globals) | `Agent`, `Dataset`, `StepBudget`, and the run logger are all constructed explicitly and passed via `RunContext[AgentDeps]` or explicit function parameters to `answer_question`; no module-level global agent instance. **Pass.** |
| Eng. Principle 5 (validated pydantic boundary) | `AgentAnswer` (the `Agent`'s structured `output_type`), `AgentRunLogEntry`, and `BudgetExhausted` are pydantic models; the four tool wrappers pass through the existing `001-data-access-tools` pydantic models unchanged as their own input/output schemas (data-model.md). **Pass.** |
| Eng. Principle 6 (tool functions testable without a model) | The plain step-budget/error-translation/outcome-clamp logic is unit-testable with no model; the tool *wrappers* themselves need `RunContext`, so their contract tests use `FunctionModel` (a scripted, non-network double) rather than a real model — satisfying the spirit (no live model call required to test) even though a `pydantic-ai` object is technically present (research.md §10). **Pass.** |
| Eng. Principle 7 (typed centralized settings) | `AgentSettings` (`pydantic-settings`) is introduced for exactly the case Engineering Principle 7 names as its example — "a different model" — with `model_name` required (no hardcoded default) so every run's exact model configuration is explicit and recorded (research.md §6). File paths (run log) stay explicit constructor arguments, matching `002`'s established DI pattern — not folded into settings speculatively. **Pass.** |
| Eng. Principle 8 (prompts/briefings versioned) | The Portuguese system prompt is a named, diffable file (`prompts/system_v1.md`), not an inline string, referenced explicitly by version (research.md §7). Dataset briefings continue to be read as-is from `002`. **Pass.** |
| Eng. Principle 9 (native instrumentation preferred) | This is the feature that finally resolves `002`'s documented, deliberate gap: `pydantic-ai` wiring now exists, so `Agent(instrument=...)` is wired for model/tool-call tracing (research.md §8). FR-013's run log remains a separate, bespoke, question-level research record — tracing spans and the per-question outcome log serve different purposes and neither replaces the other. **Pass.** |
| Eng. Principle 10 (static typing enforced) | pyright in CI (research.md §10), tracked as a task. **Pass**, pending task generation. |

No violations requiring justification. Complexity Tracking table left empty.

## Project Structure

### Documentation (this feature)

```text
specs/003-qa-agent-workflow/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── answering.md
│   ├── tools.md
│   └── errors.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
└── qa_agent/
    ├── __init__.py
    ├── settings.py          # AgentSettings (pydantic-settings) — model_name (required), instrument
    ├── models.py             # AgentAnswer (Agent output_type), AgentRunLogEntry, QuestionAnsweringResult
    ├── step_budget.py         # StepBudget — the 10-retrieval-step bound (FR-012), BudgetExhausted model
    ├── deps.py                  # AgentDeps dataclass: dataset, dataset_key, briefing, step_budget
    ├── prompts/
    │   └── system_v1.md          # Portuguese system prompt template (Eng. Principle 8)
    ├── prompt_loader.py            # renders system_v1.md with the selected briefing injected
    ├── run_log.py                    # RunLogger Protocol + JsonlRunLogger (mirrors dataset_selector/usage_log.py)
    ├── tools.py                        # @agent.tool wrappers over data_access.capabilities + ModelRetry translation
    ├── agent_factory.py                  # build_agent(settings) -> Agent[AgentDeps, AgentAnswer]
    └── capabilities.py                     # answer_question — the one public entry point

tests/
├── contract/
│   └── qa_agent/
│       ├── test_grounded_answers.py     # 1:1 with US1 Acceptance Scenarios (FunctionModel)
│       ├── test_coverage_gaps.py         # 1:1 with US2 Acceptance Scenarios
│       ├── test_multi_step.py             # 1:1 with US3 Acceptance Scenarios
│       └── test_failure_translation.py     # 1:1 with US4 Acceptance Scenarios
├── unit/
│   └── qa_agent/
│       ├── test_step_budget.py            # bound enforcement + zero-retrievals outcome clamp (FR-012)
│       ├── test_prompt_loader.py           # briefing injection into the versioned template
│       └── test_run_log.py                  # JSONL append, one line per question (FR-013)
└── fixtures/
    └── qa_agent/
        └── unreadable_dataset/               # reuses 001's "broken" source pattern for US4 scenario 1

data/
└── logs/                                       # existing, already .gitignore'd (002) — qa_agent_runs.jsonl lands here
```

**Structure Decision**: Single-project library layout, same as `001-data-access-tools` and
`002-dataset-selector` (`src/<package>/`, `tests/{contract,unit}/<package>/`,
`tests/fixtures/<package>/`) — this feature adds a sibling package, `qa_agent`, consumed
in-process alongside `data_access` and `dataset_selector` (both reused directly, research.md
§1/§2). No CLI/web surface; `answer_question` is the only public entry point a future
CLI/API layer would call.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations recorded — table intentionally left empty.
