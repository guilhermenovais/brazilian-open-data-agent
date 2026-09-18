---

description: "Task list for Testset Runner for LLM Evaluation"
---

# Tasks: Testset Runner for LLM Evaluation

**Input**: Design documents from `/specs/004-testset-runner/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (running.md, comparing.md, errors.md), quickstart.md

**Tests**: Included — plan.md's Testing section explicitly specifies pytest contract tests mirroring spec.md's Acceptance Scenarios 1:1 (quickstart.md Scenarios 1–7), plus unit tests for loader/matcher/store/comparator and one `FunctionModel`-driven `qa_agent` contract test.

**Organization**: Tasks are grouped by user story (US1/US2/US3, spec.md priorities P1/P2/P3) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

Single project (Option 1): `src/<package>/`, `tests/{contract,unit}/<package>/`, `tests/fixtures/<package>/`, matching `001`–`003`'s existing layout. This feature adds `src/testset_runner/` and makes small additive changes to `src/qa_agent/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package skeleton, gitignore entry, and the small fixture files loader/comparator tests need.

- [X] T001 Create `src/testset_runner/__init__.py` and empty module files (`models.py`, `loader.py`, `matcher.py`, `question_answerer.py`, `runner.py`, `store.py`, `comparator.py`, `exceptions.py`, `cli.py`) per plan.md's Project Structure
- [X] T002 [P] Add `data/testset_runs/` to `.gitignore`, alongside the existing `data/logs/` entry (research.md §7)
- [X] T003 [P] Create `tests/fixtures/testset_runner/mini-testset.json` — a small (3–5 question) fixture matching the bundled schema (`n`, `type`, `question`, `expected`, `source`), including at least one numeric `expected` (e.g. `"8351"`), one `~`-tolerant numeric `expected` (e.g. `"~3675300.51"`), and one non-numeric/composite `expected` (e.g. `"Agência Espacial Brasileira / Apoio Administrativo / 238959"`)
- [X] T004 [P] Create `tests/fixtures/testset_runner/missing-expected-field.json` — a fixture with one record missing the `expected` field, for FR-013 fail-fast testing (quickstart.md Scenario 5)
- [X] T005 [P] Create `tests/fixtures/testset_runner/duplicate-n.json` — a fixture with two records sharing the same `n` value, for data-model.md's duplicate-`n` rejection rule

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The additive `qa_agent` contract extensions (steps/errored, base_url) and the `testset_runner` models/exceptions/store protocol that **both** `run_testset` (US1) and `compare_runs` (US2) depend on, and that US3's target-configuration recording relies on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T006 [P] Add `RetrievalStep` pydantic model to `src/qa_agent/models.py`: `tool_name: str`, `arguments: dict`, `result_summary: str` (data-model.md)
- [X] T007 Add `steps: list[RetrievalStep] = []` and `errored: bool = False` fields to `QuestionAnsweringResult` in `src/qa_agent/models.py` (depends on T006; both fields default so existing `003` call sites/assertions are unaffected — data-model.md's Backward Compatibility note)
- [X] T008 [P] Add `base_url: str | None = None` (env `QA_AGENT_BASE_URL`) and `api_key: str | None = None` (env `QA_AGENT_API_KEY`) fields to `AgentSettings` in `src/qa_agent/settings.py` (data-model.md)
- [X] T009 Extend `build_agent` in `src/qa_agent/agent_factory.py`: when `settings.base_url` is set, construct `Agent(model=OpenAIChatModel(settings.model_name, provider=OpenAIProvider(base_url=settings.base_url, api_key=settings.api_key)), deps_type=AgentDeps, output_type=AgentAnswer)`; when `settings.base_url` is `None`, behavior stays byte-for-byte identical to today (`Agent(model=settings.model_name, ...)`) (research.md §4; depends on T008)
- [X] T010 Populate `steps` and `errored` in `src/qa_agent/capabilities.py`: in `_answer_with_selection`, after a successful `agent.run_sync` call, walk `run_result.all_messages()` for `ToolCallPart`/`ToolReturnPart` pairs to build `steps` (dumping `ToolCallPart.args` to a plain `dict` for `arguments`, and `str(...)`/`model_dump_json()` of the tool result for `result_summary`), and pass `steps` through `_finalize` into the returned `QuestionAnsweringResult`; set `errored=True` in `answer_question`'s dataset-selection `except` branch and in `_answer_with_selection`'s `agent.run_sync` `except` branch (both currently returning via `_finalize`); leave `errored=False` (the default) on every path that reaches a real `AgentAnswer`, including a legitimate `outcome="none"` (research.md §3; depends on T006, T007)
- [X] T011 [P] Contract test: `qa_agent` steps/errored extraction via `FunctionModel` in `tests/contract/qa_agent/test_retrieval_trace.py` — mirrors `tests/contract/qa_agent/test_multi_step.py`'s pattern against the real bundled dataset; asserts a scripted multi-tool-call run produces a non-empty `result.steps` with correct `tool_name`/`arguments`/`result_summary` per step, and a separate scripted model-call failure produces `result.errored is True` (depends on T010)
- [X] T012 [P] Create `src/testset_runner/exceptions.py`: `TestsetRunnerError` base class, `TestsetLoadError`, `RunLoadError`, `IncompatibleRunsError` subclasses (contracts/errors.md)
- [X] T013 Create `src/testset_runner/models.py` with all pydantic v2 models from data-model.md:
  - `Question`: `n: int` (`Field(gt=0)`), `type: str`, `question: str` (`Field(min_length=1)`), `expected: str` (`Field(min_length=1)`), `source: str`
  - `Testset`: `path: str`, `content_hash: str`, `questions: list[Question]`
  - `TargetConfiguration`: `model_name: str`, `base_url: str | None` — never an `api_key` field, by design (Constitution Principle VIII)
  - `QuestionResult`: `n: int`, `question: str`, `expected: str`, `category: str`, `actual_answer: str`, `agent_outcome: Literal["full", "partial", "none"]`, `dataset_key: str`, `steps: list[qa_agent.models.RetrievalStep]`, `match_status: Literal["matched", "not_matched", "needs_review", "errored"]`
  - `RunSummary`: `total_questions: int`, `match_rate: float`, `by_status: dict[str, int]`, `by_category: dict[str, RunSummary]` (nested entries omit their own `by_category`), `target_unreachable: bool`
  - `TestRun`: `run_id: str`, `created_at: datetime`, `testset: Testset`, `target: TargetConfiguration`, `results: list[QuestionResult]`, `summary: RunSummary`
  - `ComparisonEntry`: `n: int`, `question: str`, `status_a`/`status_b: Literal["matched", "not_matched", "needs_review", "errored"]`, `transition: Literal["newly_passing", "newly_failing", "still_passing", "still_failing", "unchanged_other"]`
  - `RunComparison`: `run_a: TargetConfiguration`, `run_b: TargetConfiguration`, `entries: list[ComparisonEntry]`, `summary: dict[str, int]`
  (depends on T006)
- [X] T014 [P] Create `src/testset_runner/store.py`: `RunStore` Protocol (`save(run: TestRun) -> str`, `load(path: str | Path) -> TestRun`) and `JsonFileRunStore(out_dir)` writing exactly one JSON file per run at `<out_dir>/<run_id>.json` (research.md §7) and reading it back, raising `RunLoadError` when a path doesn't exist or doesn't parse as a valid `TestRun` (contracts/errors.md) (depends on T012, T013)

**Checkpoint**: Foundation ready — `run_testset` (US1) and `compare_runs` (US2) can now both be implemented.

---

## Phase 3: User Story 1 - Run the sample testset and see what went wrong per question (Priority: P1) 🎯 MVP

**Goal**: A person picks a testset, model, and URL, starts a run, and gets back a report covering every question with expected vs. actual answer, match status, dataset selected, and retrieval steps.

**Independent Test**: Point a run at `data/testsets/orcamentos-aeb-csv.json` and any configured model/URL, let it finish, and confirm the report lists all 50 questions with expected vs. actual, a match indicator, and the dataset/steps used for each — without digging through raw logs.

### Tests for User Story 1

- [X] T015 [P] [US1] Contract test AS1 (quickstart.md Scenario 1): a full run against `data/testsets/orcamentos-aeb-csv.json` with a scripted `FakeAnswerer` produces a `TestRun` with `len(run.results) == 50` and `run.summary.total_questions == 50`, and a run file exists under `data/testset_runs/`, in `tests/contract/testset_runner/test_run_testset.py`
- [X] T016 [P] [US1] Contract test AS2: each `QuestionResult` carries `question`, `expected`, `actual_answer`, `agent_outcome`, `dataset_key`, `steps`, and `match_status` — sufficient to explain any single result without re-running anything, same file
- [X] T017 [P] [US1] Contract test AS3/FR-006 (quickstart.md Scenario 2): numeric `expected` values are auto-graded — `matcher.grade("8351", "O valor pago foi de R$ 8.351,00.") == "matched"`, a differing amount is `"not_matched"`, and `~`-marked approximate values match within tolerance (`matcher.grade("~3675300.51", "O total aproximado foi de R$ 3.675.300,50.") == "matched"`), in `tests/contract/testset_runner/test_run_testset.py`
- [X] T018 [P] [US1] Contract test AS4/FR-007 (quickstart.md Scenario 3): non-numeric `expected` values (descriptive text and composite `"/"`-joined multi-field facts) are always `"needs_review"`, never auto-guessed, same file
- [X] T019 [P] [US1] Contract test AS5/FR-004 (quickstart.md Scenario 4): a `FakeAnswerer` scripted so question `n=7` comes back `errored=True` still lets the run finish with all 50 results; `n=7`'s `match_status == "errored"`; every other question's `match_status != "errored"`, same file
- [X] T020 [P] [US1] Contract test FR-013 (quickstart.md Scenario 5): `run_testset` raises `TestsetLoadError` for `tests/fixtures/testset_runner/missing-expected-field.json` before any question is asked (no run file written), in `tests/contract/testset_runner/test_errors.py`
- [X] T021 [P] [US1] Contract test for the Edge Case "target unreachable for the whole run" (research.md §6): a `FakeAnswerer` scripted so every eligible question errors produces `run.summary.target_unreachable == True`; a run where only some questions error leaves it `False`, in `tests/contract/testset_runner/test_run_testset.py`
- [X] T022 [P] [US1] Unit test `TestsetLoader`: valid-schema load succeeds, `content_hash` is a stable SHA-256 hex digest of the file's raw bytes, `tests/fixtures/testset_runner/duplicate-n.json` raises `TestsetLoadError`, `tests/fixtures/testset_runner/missing-expected-field.json` raises `TestsetLoadError`, in `tests/unit/testset_runner/test_loader.py`
- [X] T023 [P] [US1] Unit test `DeterministicMatcher`/`NumericMatchStrategy`: Brazilian/US locale-format normalization (currency symbols, thousands separators, whitespace), exact vs. `~`-tolerant comparison, and every non-numeric `expected` shape (bare name, composite, descriptive) routes to `"needs_review"`, in `tests/unit/testset_runner/test_matcher.py`
- [X] T024 [P] [US1] Unit test `JsonFileRunStore`: `save` writes exactly one JSON file per run named by `run_id`, `load` round-trips an equal `TestRun`, `load` raises `RunLoadError` for a missing or malformed path, in `tests/unit/testset_runner/test_store.py`

### Implementation for User Story 1

- [X] T025 [P] [US1] Implement `TestsetLoader.load(path: str | Path) -> Testset` in `src/testset_runner/loader.py`: reads and JSON-decodes the file (wrapping `FileNotFoundError`/`json.JSONDecodeError` as `TestsetLoadError`), validates each record against `Question` (a single `pydantic.ValidationError` anywhere — including a missing `question`/`expected` per `Field(min_length=1)` — becomes `TestsetLoadError`, no partial load), rejects duplicate `n` values across the file, computes `content_hash` as the SHA-256 hex digest of the file's raw bytes (depends on T012, T013)
- [X] T026 [P] [US1] Implement `MatchStrategy` Protocol, `NumericMatchStrategy.evaluate`, and `DeterministicMatcher.grade` in `src/testset_runner/matcher.py`: strip an optional leading `~` from `expected` (marks tolerant comparison) and parse it via `data_access.numeric.parse_locale_number`; if it does not parse as a number, always return `"needs_review"`; otherwise scan `actual_answer` for numeric-looking substrings, parse each with the same function, and return `"matched"` if any parsed value equals `expected` (exact equality, or within a small relative tolerance when `~`-marked), else `"not_matched"` (research.md §5; depends on T013)
- [X] T027 [P] [US1] Implement `QuestionAnswerer` Protocol and `QaAgentQuestionAnswerer` adapter in `src/testset_runner/question_answerer.py`: constructed once per run from a `TargetConfiguration` (builds one `AgentSettings`, one `StaticDatasetSelector` (`FileBriefingSource` + `LocalDatasetLocator`), one `JsonlSelectionLogger`/`JsonlRunLogger` pair — reused across all questions, carrying only per-run configuration, never per-question state); `.answer(question: str) -> QuestionAnsweringResult` calls `qa_agent.capabilities.answer_question` (depends on T009, T010, T013)
- [X] T028 [US1] Implement `run_testset(testset_path, target, *, answerer, matcher=NumericMatchStrategy(), store) -> TestRun` in `src/testset_runner/runner.py` per contracts/running.md: calls `TestsetLoader.load` first (propagates `TestsetLoadError`, no file written on failure); loops strictly sequentially over `testset.questions`, calling `answerer.answer(question.question)` exactly once per question and passing nothing from one call's result into the next (FR-003/SC-004); sets `match_status="errored"` when `result.errored`, else `matcher.grade(question.expected, result.answer)` (a question's own failure never stops the loop — FR-004); computes `RunSummary` (`total_questions`, `match_rate`, `by_status`, `by_category`, and `target_unreachable=True` when every question that reached dataset selection successfully came back `errored`, research.md §6); calls `store.save(...)` exactly once after the full loop and returns the saved `TestRun` (depends on T025, T026, T014)
- [X] T029 [US1] Implement CLI `run` subcommand in `src/testset_runner/cli.py`: `python -m testset_runner.cli run --testset <path> --model <model_name> [--base-url <url>] [--api-key <key>] [--out-dir data/testset_runs]`, each flag falling back to its `QA_AGENT_*` environment variable (research.md §9); builds `TargetConfiguration`, `AgentSettings`, `QaAgentQuestionAnswerer`, `JsonFileRunStore(out_dir)`, calls `run_testset`, and prints a one-screen summary (overall match rate, per-category breakdown, a `target_unreachable` warning if set) plus the saved run file's path (SC-005) (depends on T027, T028)

**Checkpoint**: User Story 1 is fully functional and independently testable — a person can run the bundled testset against a chosen model/URL and get a complete, self-contained per-question report.

---

## Phase 4: User Story 2 - Compare two runs to see what changed (Priority: P2)

**Goal**: A person compares two persisted runs of the same testset and sees exactly which questions newly started passing, newly started failing, and are still failing either way.

**Independent Test**: Produce two runs of the same testset (e.g., against two different models), request a comparison, and confirm the result lists newly-passing/newly-failing/still-failing questions without manual cross-referencing.

### Tests for User Story 2

- [X] T030 [P] [US2] Contract test AS1/SC-003 (quickstart.md Scenario 6): comparing two persisted runs of the same testset produces `len(comparison.entries) == 50` and `sum(comparison.summary.values()) == 50` (every question accounted for, not just changed ones), in `tests/contract/testset_runner/test_compare_runs.py`
- [X] T031 [P] [US2] Contract test AS2: `RunComparison.run_a`/`run_b` state each run's `model_name`/`base_url` directly, so a person never needs to re-open either saved `TestRun` file, same file
- [X] T032 [P] [US2] Contract test AS3/FR-011 (quickstart.md Scenario 7): comparing a run made from `mini-testset.json` against a run made from an edited copy of the same file (same name, different content) raises `IncompatibleRunsError` before any `ComparisonEntry` is built, in `tests/contract/testset_runner/test_errors.py`
- [X] T033 [P] [US2] Contract test: `compare_runs` raises `RunLoadError` when either given path doesn't exist or doesn't parse as a saved `TestRun`, same file
- [X] T034 [P] [US2] Unit test `compare_runs`'s transition-bucket logic in `tests/unit/testset_runner/test_comparator.py`: `matched→matched` = `still_passing`; any not-matched-family→`matched` = `newly_passing`; `matched`→any not-matched-family = `newly_failing`; not-matched-family→not-matched-family (same or different member) = `still_failing`; `needs_review`/`errored` pairs with `status_a == status_b` and no matched-crossing = `unchanged_other`; and hash-gating (mismatched `content_hash` raises before any entry is built)

### Implementation for User Story 2

- [X] T035 [US2] Implement `compare_runs(run_a_path, run_b_path, *, store) -> RunComparison` in `src/testset_runner/comparator.py` per contracts/comparing.md: loads both runs via `store.load` (propagating `RunLoadError`); checks `run_a.testset.content_hash == run_b.testset.content_hash`, raising `IncompatibleRunsError` before building any entry on a mismatch; joins `QuestionResult`s by `n` into one `ComparisonEntry` per question (always the full question count, never just the changed subset) with the derived `transition` per the rule above; builds `RunComparison.summary` as per-transition counts that always sum to `len(entries)` (depends on T014, T013)
- [X] T036 [US2] Implement CLI `compare` subcommand in `src/testset_runner/cli.py`: `python -m testset_runner.cli compare <run_a.json> <run_b.json>`, calls `compare_runs`, and prints which questions newly passed, newly failed, or are still failing between the two runs, plus each run's `model`/`base_url` (depends on T035)

**Checkpoint**: User Stories 1 AND 2 both work independently — runs can be produced and meaningfully compared.

---

## Phase 5: User Story 3 - Point a run at a different model or endpoint without touching code (Priority: P3)

**Goal**: A person tries the same testset against a different model or provider/endpoint purely via CLI flags, with no source edits and no re-exporting environment variables between two runs in the same session.

**Independent Test**: Start two runs of the same testset that only differ in `--model`/`--base-url`, and confirm both complete and each persisted run's `target` clearly states the model and URL used.

### Tests for User Story 3

- [X] T037 [P] [US3] Contract test AS1/AS2: two `run_testset` calls differing only in `TargetConfiguration.model_name`/`base_url` both complete successfully, and each returned `TestRun.target` records the exact `model_name`/`base_url` passed in, in `tests/contract/testset_runner/test_run_testset.py`
- [X] T038 [P] [US3] Unit test: `cli.py`'s `run` subcommand argument parser accepts `--model`, `--base-url`, and `--api-key` as explicit flags (no environment variable required when flags are given) and produces the matching `TargetConfiguration`, in `tests/unit/testset_runner/test_cli.py`

### Implementation for User Story 3

- [X] T039 [US3] Confirm/finish `src/testset_runner/cli.py`'s `--model`/`--base-url`/`--api-key` flag wiring into `TargetConfiguration`/`AgentSettings` (already scaffolded by T029) so both flag-only and env-var-fallback invocations work per research.md §9, closing any gap surfaced by T037/T038 (depends on T029, T037, T038)

**Checkpoint**: All three user stories are independently functional — running, comparing, and freely re-targeting a run all work without source edits.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification across the whole feature.

- [X] T040 [P] Run `pyright src/` and fix any type errors introduced by the `qa_agent` additive changes or the new `testset_runner` package (Constitution Principle IX/X)
- [X] T041 [P] Run the full deterministic suite — `pytest tests/contract/testset_runner tests/unit/testset_runner tests/contract/qa_agent tests/unit/qa_agent -v` — and fix any failures (quickstart.md "Done when"); no CI workflow change is needed since `.github/workflows/ci.yml` already globs `tests/contract`/`tests/unit` and `src/`
- [ ] T042 Execute quickstart.md's live-model track manually (`python -m testset_runner.cli run --testset data/testsets/orcamentos-aeb-csv.json --model <model> [--base-url <url>]` against a real configured model, then `cli.py compare` on the two resulting run files) to sanity-check SC-001/SC-002/SC-005/SC-006 end-to-end; documented follow-on, not part of the CI gate — **not run in this session: no `OPENAI_API_KEY`/`QA_AGENT_MODEL` configured in the environment**

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational. No dependency on US2/US3.
- **User Story 2 (Phase 4)**: Depends on Foundational (needs `RunStore`, `TestRun`/`ComparisonEntry`/`RunComparison` models). Does not require US1's `runner.py` to be implemented, but in practice needs at least two saved `TestRun` files to compare — tests build their own via a fake `QuestionAnswerer` and `run_testset`/`JsonFileRunStore`, so it is developed after or alongside US1.
- **User Story 3 (Phase 5)**: Depends on Foundational (needs `base_url`/`api_key` on `AgentSettings`, T008/T009) and on US1's `cli.py run` subcommand (T029) existing to extend.
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

### Within Each User Story

- Tests are written first (and should fail before implementation exists).
- Models/exceptions/store (Foundational) before loader/matcher/answerer (US1) before `runner.py` (US1) before `cli.py run` (US1).
- `comparator.py` (US2) depends only on Foundational's `store.py`/`models.py`, not on `runner.py`.

### Parallel Opportunities

- All Setup tasks marked [P] (T002–T005) can run in parallel.
- Within Foundational: T006, T008, T012 can start in parallel; T007 depends on T006; T009 depends on T008; T010 depends on T006+T007; T013 depends on T006; T014 depends on T012+T013; T011 depends on T010.
- Once Foundational completes, US1's test tasks (T015–T024) can all be written in parallel (different assertions, mostly shared files but no code dependency between them); US1's implementation tasks T025/T026/T027 can proceed in parallel (different files), with T028 waiting on all three and T029 waiting on T028.
- US2's tests (T030–T034) can run in parallel once Foundational is done; US3's tests (T037–T038) can run in parallel once Foundational + T029 are done.
- US2 and US3 can be developed in parallel by different people once US1's Foundational-level pieces (not US1's own `runner.py`/`cli.py`) are in place — though US3's `cli.py` task (T039) specifically extends US1's T029 file.

---

## Parallel Example: Foundational Phase

```bash
# Launch independent foundational tasks together:
Task: "Add RetrievalStep model to src/qa_agent/models.py"          # T006
Task: "Add base_url/api_key fields to AgentSettings"                # T008
Task: "Create testset_runner/exceptions.py"                          # T012
```

## Parallel Example: User Story 1 Implementation

```bash
# Once T025/T026/T027's own dependencies (Foundational) are done:
Task: "Implement TestsetLoader in src/testset_runner/loader.py"           # T025
Task: "Implement MatchStrategy/NumericMatchStrategy/DeterministicMatcher"   # T026
Task: "Implement QuestionAnswerer/QaAgentQuestionAnswerer adapter"           # T027
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (CRITICAL — blocks everything).
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: run the deterministic suite (T015–T024) plus a manual live-model run against the bundled testset; confirm a full 50-question report is produced.
5. This alone is a usable MVP (spec.md: "This alone is a usable MVP").

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. Add User Story 1 → validate independently → usable MVP.
3. Add User Story 2 → validate independently → runs are now comparable.
4. Add User Story 3 → validate independently → re-targeting a run needs no source edits.
5. Polish.

### Suggested MVP Scope

User Story 1 (Phases 1–3, tasks T001–T029) — a full, trustworthy per-question report from a single run is the entire point of the feature per spec.md.
