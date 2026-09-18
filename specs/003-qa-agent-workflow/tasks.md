---

description: "Task list template for feature implementation"
---

# Tasks: Question-Answering Agent Workflow

**Input**: Design documents from `/specs/003-qa-agent-workflow/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (answering.md,
tools.md, errors.md), quickstart.md — all present.

**Tests**: Explicitly requested by plan.md/research.md §10 (contract tests mirroring
spec.md's Acceptance Scenarios 1:1, plus unit tests for the plain-Python mechanisms) — the
model-quality evaluation harness (research.md §11) is separately called out as a
non-CI-gated follow-on and is included in Polish.

**Organization**: Because this feature's whole point is one shared orchestration flow
(`answer_question`) reused identically by every user story, all shared implementation lives
in Phase 2 (Foundational) — exactly matching plan.md's Project Structure, which names one
file per module, not per story. Each user story phase (3–6) then adds the contract tests that
prove that shared flow satisfies that story's Acceptance Scenarios, per plan.md's own
one-test-file-per-story layout, and is independently runnable/checkable once Phase 2 is done.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

Single project (Python library), matching `001-data-access-tools`/`002-dataset-selector`:
`src/<package>/`, `tests/{contract,unit}/<package>/`, `tests/fixtures/<package>/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Bring in the one new dependency this feature needs and scaffold the package.

- [X] T001 Add `pydantic-ai` and `pydantic-settings` to `[project] dependencies` in
      `pyproject.toml` (alongside the existing `pydantic>=2`/`pandas>=2`) — this is the first
      feature in the codebase to import `pydantic_ai`/`pydantic_settings` (plan.md, research.md
      §1/§6).
- [X] T002 [P] Create the `src/qa_agent/` package with an empty `src/qa_agent/__init__.py`.
- [X] T003 [P] Create the `src/qa_agent/prompts/` directory to hold the versioned system
      prompt template (Engineering Principle 8).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the complete `answer_question` wiring — settings, models, step budget,
deps, prompt, run log, tool wrappers, agent factory, and the public capability itself — plus
unit tests for every plain-Python piece. This is the entire feature's business logic; every
user story phase below only adds tests that exercise it.

**⚠️ CRITICAL**: No user story test can pass until this phase is complete.

- [X] T004 [P] Define `AgentSettings` in `src/qa_agent/settings.py` as a
      `pydantic_settings.BaseSettings` subclass with `model_config =
      SettingsConfigDict(env_prefix="QA_AGENT_")`: `model_name: str` with **no default**
      (required — env var `QA_AGENT_MODEL`, "no hardcoded default so every run's exact model
      configuration is explicit and recorded", research.md §6) and `instrument: bool = True`
      (env var `QA_AGENT_INSTRUMENT`), per data-model.md's `AgentSettings` table.

- [X] T005 [P] Define `AgentAnswer`, `QuestionAnsweringResult`, and `AgentRunLogEntry` as
      `pydantic` v2 `BaseModel`s in `src/qa_agent/models.py` (data-model.md):
      - `AgentAnswer`: `answer: str = Field(min_length=1)` — "must be non-empty... an empty
        string is never a valid final answer, even for the 'cannot answer' case (the
        explanation text itself is the answer)"; `outcome: Literal["full", "partial",
        "none"]`.
      - `QuestionAnsweringResult`: `answer: str`, `dataset_key: str`, `outcome:
        Literal["full", "partial", "none"]`.
      - `AgentRunLogEntry`: `question: str`, `dataset_key: str`, `outcome: Literal["full",
        "partial", "none"]`, `timestamp: datetime`.

- [X] T006 [P] Define `StepBudget` (plain class — "it never crosses one [a boundary] — it's
      pure in-process orchestration state") and `BudgetExhausted` (`pydantic` model) in
      `src/qa_agent/step_budget.py`:
      - Module constant `RETRIEVAL_STEP_LIMIT = 10` (FR-012, "a fixed value... rather than
        something the user can configure per question").
      - `StepBudget(limit: int)` with `attempts: int` and `successes: int` counters;
        `try_reserve() -> bool` — "returns `True` and increments `attempts` if `attempts <
        limit`, else returns `False` and leaves `attempts` unchanged"; `record_success() ->
        None` — "increments `successes`", called "only when the wrapped `data_access`
        capability call actually returns a result without raising".
      - `BudgetExhausted`: `message: str` — fixed Portuguese text telling the model the step
        budget is exhausted and it must finalize its answer now with whatever it already
        retrieved.

- [X] T007 Define `AgentDeps` in `src/qa_agent/deps.py` as a plain `@dataclass` (not
      `pydantic` — it never crosses the tool boundary): `dataset: data_access.dataset.Dataset`,
      `dataset_key: str`, `step_budget: StepBudget` (data-model.md). Depends on T006.

- [X] T008 [P] Write the Portuguese system prompt template at
      `src/qa_agent/prompts/system_v1.md` (Engineering Principle 8 — "named, diffable, and
      referenced explicitly... never edited in place"): fixed instructions to answer only in
      Portuguese; never state a number, name, or fact not obtained from a retrieval performed
      during this same request (FR-005); when a question is ambiguous between dataset
      fields/metrics, state which interpretation was used (FR-010); translate any technical
      failure into a plain, non-technical explanation; never mention internal file names,
      column names, or dataset identifiers in the final `answer`; one placeholder for the
      selected dataset's briefing text to be injected at render time. Depends on T003.

- [X] T009 Implement `render(briefing: str) -> str` in `src/qa_agent/prompt_loader.py`: loads
      `prompts/system_v1.md` and substitutes the briefing placeholder with the given briefing
      text (FR-003 — "use the selected dataset's briefing to interpret the question... so the
      user is never required to know or name any technical schema detail"). Depends on T008.

- [X] T010 [P] Define `RunLogger` (`Protocol` with `log(entry: AgentRunLogEntry) -> None`)
      and `JsonlRunLogger` in `src/qa_agent/run_log.py`, mirroring
      `dataset_selector/usage_log.py`'s `SelectionLogger`/`JsonlSelectionLogger` exactly:
      `JsonlRunLogger(log_path: str | Path)` creates parent directories as needed and appends
      one `entry.model_dump_json()` line per call (FR-013). Depends on T005.

- [X] T011 Implement the four `@agent.tool` wrappers — `discover_data_sources`,
      `inspect_schema`, `query_rows`, `aggregate_rows` — in `src/qa_agent/tools.py`
      (contracts/tools.md), each taking `ctx: RunContext[AgentDeps]` plus the same parameters
      as the matching `data_access.capabilities` function it wraps unchanged: (1) call
      `ctx.deps.step_budget.try_reserve()`; if it returns `False`, return
      `BudgetExhausted(message=...)` immediately **without** calling the underlying capability
      (FR-012); (2) otherwise call the matching `data_access.capabilities.*` function against
      `ctx.deps.dataset`; (3) on success, call `ctx.deps.step_budget.record_success()` and
      return the capability's result model as-is; (4) on any
      `data_access.exceptions.DataAccessError` subclass, raise `pydantic_ai.ModelRetry` with a
      message naming the problem (research.md §4) — this consumes one budget unit regardless
      of outcome since `try_reserve()` already ran in step 1. Register each tool with
      `retries=10` so `pydantic-ai`'s own retry ceiling never terminates a run before
      `StepBudget` does. Depends on T006, T007.

- [X] T012 Implement `build_agent(settings: AgentSettings) -> Agent[AgentDeps, AgentAnswer]`
      in `src/qa_agent/agent_factory.py`: constructs an `Agent` with `model=settings.model_name`,
      `deps_type=AgentDeps`, `output_type=AgentAnswer`, `instrument=settings.instrument`, and
      registers the four tool wrappers from `tools.py`. `build_agent` itself is briefing-agnostic
      (same wiring for every question); rendering `prompt_loader.render(briefing)` and passing it
      as `instructions=` on `agent.run_sync` is the caller's job (`capabilities.py`, T013), since
      the briefing is only known once dataset selection has completed for that question
      (Engineering Principle 4 — "no module-level global agent instance"; a fresh `Agent` is
      still built by every `answer_question` call). Depends on T004, T005, T007, T009, T011.

- [X] T013 Implement `answer_question(question: str, *, selector: DatasetSelector,
      selection_logger: SelectionLogger, run_logger: RunLogger, settings: AgentSettings) ->
      QuestionAnsweringResult` in `src/qa_agent/capabilities.py` per contracts/answering.md and
      data-model.md's control flow:
      1. Call `dataset_selector.capabilities.select_dataset(question, selector,
         selection_logger)` exactly once, before building any `Agent`.
      2. **Tier 1**: on `dataset_selector.exceptions.{NoBriefingsAvailableError,
         DatasetNotFoundError, BriefingNotFoundError}`, skip straight to step 6 with a fixed
         Portuguese "não foi possível determinar a base de dados para responder a esta
         pergunta" answer, `outcome="none"`, `dataset_key="<none>"` — no `Agent` is
         constructed and no model call happens.
      3. Otherwise build `AgentDeps(dataset, dataset_key, StepBudget(limit=10))`, build the
         `Agent` via `agent_factory.build_agent(settings)`, and call `agent.run_sync(question,
         deps=deps)`.
      4. **Tier 3**: wrap that call in a catch-all `except Exception` (covers
         `pydantic_ai.exceptions.UnexpectedModelBehavior`, provider HTTP/network/timeout
         errors, and any other exception escaping `agent.run`) — on any of these, use a fixed
         Portuguese "não foi possível processar a pergunta no momento" answer, `outcome="none"`
         (no partial-answer synthesis attempted, since the model's own synthesis step never
         completed — research.md §10).
      5. On success, apply the deterministic clamp (research.md §5): if
         `deps.step_budget.successes == 0`, force `outcome="none"` regardless of what the
         model's `AgentAnswer.outcome` reported.
      6. Always write exactly one `AgentRunLogEntry(question, dataset_key, outcome,
         timestamp=datetime.now(timezone.utc))` via `run_logger.log(...)` — on every path,
         including Tier 1/3 failures — before returning `QuestionAnsweringResult(answer,
         dataset_key, outcome)`. Never let a `DatasetSelector*`, `DataAccessError`, or
         `pydantic_ai` exception propagate to the caller.
      Depends on T004, T005, T006, T007, T009, T010, T011, T012.

- [X] T014 [P] Unit tests for `StepBudget` and the outcome clamp in
      `tests/unit/qa_agent/test_step_budget.py` (quickstart.md Scenarios 2–3): assert
      `try_reserve()` returns `True` for exactly 10 calls then `False` on the 11th, without
      further incrementing `attempts`; assert a budget with zero `record_success()` calls
      forces the clamp to `outcome="none"` even when the reported outcome is `"full"`
      (exercise the clamp via `qa_agent.capabilities`'s internal helper, e.g. `_clamp_outcome`).
      Depends on T006, T013.

- [X] T015 [P] Unit tests for `prompt_loader.render` in
      `tests/unit/qa_agent/test_prompt_loader.py`: assert the rendered output contains the
      given briefing text verbatim and the fixed Portuguese instructions from
      `system_v1.md`. Depends on T009.

- [X] T016 [P] Unit tests for `JsonlRunLogger` in `tests/unit/qa_agent/test_run_log.py`,
      mirroring `tests/unit/dataset_selector/test_usage_log.py`'s style: assert one JSON line
      is appended per `log()` call and that it contains `question`, `dataset_key`, `outcome`,
      and `timestamp` keys. Depends on T010.

**Checkpoint**: The full `answer_question` wiring exists and its plain-Python mechanisms
(step budget, prompt rendering, run logging) are unit-tested with no model involved. User
story contract tests below exercise this same wiring through `answer_question` itself.

---

## Phase 3: User Story 1 - Get a grounded answer to a covered question (Priority: P1) 🎯 MVP

**Goal**: A Portuguese question fully within the selected dataset's coverage gets answered
correctly in Portuguese, using only retrieved facts, with no internal details leaked.

**Independent Test**: Submit "Quanto foi pago pela AEB em 2015?" (quickstart.md Scenario 1)
and confirm the answer is Portuguese, matches the real underlying data, and requires no
dataset/field knowledge from the caller.

### Tests for User Story 1

- [X] T017 [P] [US1] Contract tests for Acceptance Scenarios 1–3 in
      `tests/contract/qa_agent/test_grounded_answers.py`, using
      `pydantic_ai.models.function.FunctionModel` against the real
      `data/briefings/orcamentos-aeb-csv.md` briefing and `data/datasets/orcamentos-aeb-csv`
      dataset (mirroring `tests/contract/dataset_selector/test_selection.py`'s
      `REPO_ROOT`/real-fixture pattern and quickstart.md Scenario 1):
      - AS1: a `FunctionModel` scripted to call `aggregate_rows` then answer for "Quanto foi
        pago pela AEB em 2015?" returns `outcome="full"` with a Portuguese answer whose value
        matches the real data, and `deps.step_budget.successes == 1`.
      - AS2: the same fact asked with an everyday synonym ("gasto" instead of "empenhado")
        still resolves to the correct field and returns the same correct value and `"full"`
        outcome.
      - AS3: a single-value question's `AgentAnswer.answer` never contains a file name,
        column name, or dataset identifier substring (e.g. `"tb_geral.csv"`,
        `"orcamentos-aeb-csv"`).
      - Also assert exactly one `AgentRunLogEntry` is appended per call (FR-013), reusing the
        `tmp_path`-logger pattern from `test_selection.py`.
      Depends on T013.

**Checkpoint**: User Story 1 is fully functional and independently testable — a real covered
question gets a correct grounded Portuguese answer through the complete wiring.

---

## Phase 4: User Story 2 - Clearly decline when the data doesn't cover the question (Priority: P2)

**Goal**: Out-of-coverage questions get a clear Portuguese refusal with no fabricated figure;
partially-covered questions get the covered part plus an explicit gap statement.

**Independent Test**: Submit a question fully outside the sample dataset's documented
coverage (e.g. a different ministry, or a year outside 2000–2019) and confirm a clear
Portuguese "data doesn't cover this" statement with no invented figure.

### Tests for User Story 2

- [X] T018 [P] [US2] Contract tests for Acceptance Scenarios 1–4 in
      `tests/contract/qa_agent/test_coverage_gaps.py`, using `FunctionModel` against the real
      dataset/briefing:
      - AS1: a question about a subject the briefing explicitly excludes (e.g. "Quanto o
        Ministério da Saúde gastou em 2015?" — the briefing at
        `data/briefings/orcamentos-aeb-csv.md` names only AEB and MCTIC) → `outcome="none"`,
        Portuguese statement that the data doesn't cover it, no invented figure.
      - AS2: a question about a year outside the dataset's documented 2000–2019 range →
        `outcome="none"`, no extrapolated value.
      - AS3: a question asking for an untracked granularity (e.g. a monthly or per-supplier
        breakdown, which the briefing states isn't tracked) → `outcome="none"`, no
        approximated figure derived from the coarser yearly total.
      - AS4: a `FunctionModel` scripted to retrieve one of two requested facts then report
        `outcome="partial"` → the final answer states the covered fact and explicitly names,
        in Portuguese, what couldn't be answered and why.
      - Also assert exactly one `AgentRunLogEntry` is appended per call with the corresponding
        clamped/reported outcome (FR-013).
      Depends on T013.

**Checkpoint**: User Stories 1 and 2 both work independently — grounded answers and coverage
refusals/partial answers are both correct on top of the shared wiring.

---

## Phase 5: User Story 3 - Answer questions that require multiple retrieval steps (Priority: P3)

**Goal**: Questions needing structure-discovery, filtering, and aggregation in sequence are
handled by the agent itself, in one coherent final Portuguese answer.

**Independent Test**: Submit "Qual ação teve o maior valor pago em 2015?" and confirm the
agent performs the necessary filter/aggregate steps itself and returns one correct answer.

### Tests for User Story 3

- [X] T019 [P] [US3] Contract tests for Acceptance Scenarios 1–3 in
      `tests/contract/qa_agent/test_multi_step.py`, using `FunctionModel` scripted
      multi-tool-call sequences against the real dataset:
      - AS1: a scripted sequence of `query_rows` (filter by year/unit) then `aggregate_rows`
        (sum) before the final answer; assert the final Portuguese answer states the correctly
        computed value and `deps.step_budget.attempts >= 2`.
      - AS2: a scripted sequence that retrieves enough grouped/aggregated data to determine a
        true maximum/minimum (not a partial or unsorted sample) and states it correctly.
      - AS3: a scripted sequence where `inspect_schema` is called before the subsequent
        `query_rows`/`aggregate_rows` call in the same run, asserting both tool calls actually
        executed (via the recorded call order in the `FunctionModel` script, or
        `deps.step_budget.attempts >= 2`) — nothing in `tools.py` prevents this ordering
        (contracts/tools.md).
      Depends on T013.

**Checkpoint**: User Stories 1–3 are all independently functional — single-fact, coverage-gap,
and multi-step questions are all handled correctly.

---

## Phase 6: User Story 4 - Translate technical failures into plain Portuguese (Priority: P4)

**Goal**: Every failure tier (dataset-selection failure, retrieval-tool failure, catastrophic
model-call failure) surfaces as a plain, non-technical Portuguese explanation — never raw
error text/paths/identifiers, and never presented as a complete or guessed success.

**Independent Test**: Force an unreadable data source mid-question and confirm the user-facing
response is a plain Portuguese explanation with no raw technical error text, file paths, or
internal identifiers.

### Tests for User Story 4

- [X] T020 [P] [US4] Create failure-path fixtures:
      - `tests/fixtures/qa_agent/no_briefings/` — an empty directory (a `FileBriefingSource`
        over it has zero registered keys), for the Tier 1 `NoBriefingsAvailableError` case
        (quickstart.md Scenario 4).
      - `tests/fixtures/qa_agent/unreadable_dataset/` — a briefing markdown file plus a
        dataset folder containing one malformed CSV source (reuse
        `tests/fixtures/data_access/sample_dataset/broken.csv`'s unclosed-quote pattern, which
        `Dataset.read()` turns into `UnreadableSourceError`), for the Tier 2 case.

- [X] T021 [US4] Contract tests for Acceptance Scenarios 1–2 in
      `tests/contract/qa_agent/test_failure_translation.py`, covering all three tiers from
      contracts/errors.md:
      - Tier 1 (AS1): using the `no_briefings` fixture with `StaticDatasetSelector`,
        `answer_question` returns `outcome="none"` with a plain Portuguese explanation
        containing no raw error text/paths/identifiers, and no `Agent`/model call is ever
        attempted (use a `FunctionModel` that raises if invoked, to prove it's never called).
      - Tier 2 (AS1): using the `unreadable_dataset` fixture with a `FunctionModel` scripted
        to call a tool against the broken source (triggering the wrapper's internal
        `ModelRetry`) and then produce a final answer, confirm the final Portuguese answer
        contains no raw error text, file path, or identifier, and the run still completes
        normally (not a crash).
      - Tier 3 (AS2): a `FunctionModel` that raises during `agent.run` (e.g. simulating
        `pydantic_ai.exceptions.UnexpectedModelBehavior` or a generic exception), confirm
        `answer_question` catches it, returns the fixed Portuguese "não foi possível
        processar" `outcome="none"` result, and does **not** present a partial/guessed result
        as complete.
      - Also assert exactly one `AgentRunLogEntry` is appended on each of the three tiers
        (FR-013 — "no carve-out for failed ones").
      Depends on T020, T013.

**Checkpoint**: All four user stories are independently functional — the feature is complete
per spec.md.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Type-check the finished package, and stand up the documented (non-CI-gated)
model-quality evaluation harness follow-on (research.md §11).

- [X] T022 [P] Run `pyright src/` and fix any type errors in the new `qa_agent` package
      (Engineering Principle 10; `pydantic-ai`'s own stubs make `Agent[AgentDeps,
      AgentAnswer]`'s generics checkable the same way existing `Protocol`s already are).

- [X] T023 [P] Implement the live-model evaluation harness at `src/qa_agent/eval_harness.py`
      (research.md §11, quickstart.md "Live-model track") as a reusable, re-runnable script —
      not an ad hoc manual check (Constitution Principle I): reads `QA_AGENT_MODEL` and the
      provider's own API key from the environment, runs `answer_question` against the fixed
      question set from quickstart.md ("Quanto foi pago pela AEB em 2015?", "Quanto foi gasto
      pela AEB em 2015?", "Quanto o Ministério da Saúde gastou em 2015?", "Qual ação teve o
      maior valor pago em 2015?", "Me fale sobre o orçamento."), and records each result
      alongside the full `AgentSettings` used and a timestamp for manual review. Explicitly
      **not** part of the `pytest`/CI gate (no task wires it into `.github/workflows/ci.yml`).

- [X] T024 Run the full deterministic suite end-to-end per quickstart.md's "Done when":
      `pytest tests/contract/qa_agent tests/unit/qa_agent -v` and `pyright src/`; confirm every
      test named in T014–T021 passes with zero network access and zero errors.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories. This phase contains
  essentially all of this feature's implementation, since every user story exercises the same
  single `answer_question` flow.
- **User Stories (Phases 3–6)**: All depend on Foundational (Phase 2) completion. Each phase
  is otherwise independent of the others (different test files, no shared code changes) and
  can proceed in any order or in parallel.
- **Polish (Phase 7)**: Depends on all four user story phases being complete.

### Within Phase 2 (Foundational)

- T004, T005, T006 have no dependencies on each other — parallelizable.
- T007 depends on T006 (`StepBudget` type).
- T008 depends on T003; T009 depends on T008.
- T010 depends on T005 (`AgentRunLogEntry`).
- T011 depends on T006, T007.
- T012 depends on T004, T005, T007, T009, T011.
- T013 depends on T004–T012 (the whole prior chain).
- T014 depends on T006, T013 (the clamp helper lives in `capabilities.py`).
- T015 depends on T009; T016 depends on T010.

### Within Each User Story Phase

- Every story's contract test task depends only on T013 (the finished `answer_question`),
  plus, for US4, the fixtures created in T020.

### Parallel Opportunities

- T002, T003 (Setup) in parallel.
- T004, T005, T006 (Foundational) in parallel.
- T014, T015, T016 (Foundational unit tests) in parallel once their respective dependencies
  land.
- T017, T018, T019, T020 in parallel once T013 is done (each touches a distinct file); T021
  then follows T020.
- T022, T023 (Polish) in parallel.

---

## Parallel Example: Foundational Phase

```bash
# Launch independent Foundational modules together:
Task: "Define AgentSettings in src/qa_agent/settings.py"
Task: "Define AgentAnswer, QuestionAnsweringResult, AgentRunLogEntry in src/qa_agent/models.py"
Task: "Define StepBudget and BudgetExhausted in src/qa_agent/step_budget.py"
```

## Parallel Example: User Story Test Files

```bash
# Once T013 (answer_question) is done, launch all four story-level contract test files together:
Task: "Contract tests for US1 in tests/contract/qa_agent/test_grounded_answers.py"
Task: "Contract tests for US2 in tests/contract/qa_agent/test_coverage_gaps.py"
Task: "Contract tests for US3 in tests/contract/qa_agent/test_multi_step.py"
Task: "Failure-path fixtures for US4 in tests/fixtures/qa_agent/"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational — this delivers the entire working `answer_question`
   pipeline (it cannot be meaningfully split smaller than this for a single-flow feature).
3. Complete Phase 3: User Story 1 — prove grounded answers work.
4. **STOP and VALIDATE**: run `pytest tests/contract/qa_agent/test_grounded_answers.py -v`.

### Incremental Delivery

1. Setup + Foundational → the full pipeline exists and is unit-tested.
2. Add User Story 1 tests → validate the MVP path.
3. Add User Story 2 tests → validate anti-fabrication/coverage-gap behavior.
4. Add User Story 3 tests → validate multi-step retrieval.
5. Add User Story 4 tests (plus its fixtures) → validate failure translation.
6. Polish → type-check, add the opt-in evaluation harness, run the full suite.

### Notes

- [P] tasks = different files, no dependencies.
- Because this feature is one shared orchestration flow, "independent per-story
  implementation" doesn't apply the way it would in a multi-endpoint API — independence here
  means each story's *test file* can be written, run, and reasoned about without needing the
  others, which all four contract test files satisfy.
- Verify tests fail (import errors are expected) before Phase 2 implementation exists; verify
  they pass once it does.
- Commit after each task or logical group.
