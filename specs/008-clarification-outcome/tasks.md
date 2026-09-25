---

description: "Task list for 008 Clarification Outcome, Prompt v2 and Outcome-Based Grading"
---

# Tasks: Clarification Outcome, Prompt v2 and Outcome-Based Grading

**Input**: Design documents from `/specs/008-clarification-outcome/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/grading.md, contracts/prompt-v2.md, contracts/prompt-version-and-run-record.md, quickstart.md

**Tests**: Included. The plan (Constitution Principle IV) and the contracts' "Test obligations" require one test per acceptance scenario, named `test_008_us<N>_<M>_...`, plus named edge-case tests (the `contains_amount` table, invalid expected outcome, SC-007 regrade, v1 SHA-256 pin). Every deterministic test runs without a model (FR-020, Eng. 6). Agent-path tests use the existing scripted-model seam `_answer_with_selection(model_override=...)`. The model-quality criteria (SC-001–SC-005, SC-008) are live runs outside CI (quickstart §3), done in the Polish phase.

**Organization**: Tasks are grouped by user story, so each story can be implemented and tested on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: The user story the task belongs to (US1, US2, US3, US4)
- All paths are relative to the repository root (single project, `src/` layout)

## Hard constraints (apply to every task)

- `src/qa_agent/prompts/system_v1.md` MUST stay byte-identical (FR-005). T001 pins it before anything else changes.
- Stored runs and JSONL logs MUST load unchanged (FR-003). Every new model field is optional with default `None`; `Outcome` only widens the literal.
- Grading for records without `expected_outcome` MUST NOT change (FR-016).
- Dataset-specific wording goes in `data/briefings/orcamentos-aeb-csv.md`, never in `system_v2.md` or code (Principle V).
- No new dependency. Use `hashlib` and `re` from the standard library.
- If a live acceptance run fails: change `system_v2.md` or the briefing and do a new pair of runs. Never change the grader to make a run pass.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Pin what must not change, and add the committed fixtures later tests need.

- [X] T001 Add `test_008_system_v1_sha256_is_pinned` to tests/unit/qa_agent/test_prompt_loader.py: compute `hashlib.sha256((Path(qa_agent.prompt_loader.__file__).parent / "prompts" / "system_v1.md").read_bytes()).hexdigest()` and assert it equals a literal taken from the current file (run `sha256sum src/qa_agent/prompts/system_v1.md` now, before any other change, and paste the hex). This test must pass before and after the feature.
- [X] T002 [P] Create tests/fixtures/testset_runner/008-sample-run.json: a trimmed copy of the local run `data/testset_runs/20260924T121028315459Z.json`. Keep every top-level field exactly as stored (`target`, `testset` identity/`content_hash`, `summary`, retry policy, etc.) and keep only the `results` entries for n=28, n=29, n=48, n=49, n=50 plus 2–3 other results with different `match_status` values (at least one `matched`, one `not_matched`, one `needs_review`). Do not edit any kept value (it is a backward-compatibility fixture for SC-006/SC-007). If `summary` counts no longer match the kept results, leave them unchanged; the fixture only needs to load and to regrade.
- [X] T003 [P] Create tests/fixtures/testset_runner/invalid-expected-outcome.json: copy the shape of tests/fixtures/testset_runner/mini-testset.json and set `"expected_outcome": "maybe"` on one record (keep all other records valid).

**Checkpoint**: v1 prompt is pinned; fixtures exist.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared `Outcome` type, the version-aware prompt loader, and the v2 prompt file skeleton. Every story depends on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 In src/qa_agent/models.py define `Outcome = Literal["full", "partial", "none", "needs_clarification"]` once (with a short comment listing the four meanings from data-model.md) and use it for `AgentAnswer.outcome`, `QuestionAnsweringResult.outcome` and `AgentRunLogEntry.outcome`, replacing the written-out `Literal["full", "partial", "none"]`. Do not add any other field here (the fingerprint field is T039). Update the `AgentAnswer.outcome` field description (the model sees it) to define all four values, including "needs_clarification: a pergunta tem mais de uma leitura com valores diferentes; a resposta é uma pergunta de esclarecimento sem valores".
- [X] T005 In src/qa_agent/capabilities.py change the type hints of `_clamp_outcome(reported=..., budget=...)` and `_finalize(outcome=...)` from `Literal["full", "partial", "none"]` to `Outcome` (imported from `qa_agent.models`). Behavior is unchanged in this task (the exemption is T012). Remove the `Literal` import if it becomes unused.
- [X] T006 [P] In src/testset_runner/models.py change `QuestionResult.agent_outcome` from the written-out literal to `Outcome` imported from `qa_agent.models` (no other field changes in this task).
- [X] T007 [P] Create src/qa_agent/exceptions.py with `class UnknownPromptVersionError(ValueError)`: `__init__(self, requested: str, available: list[str])` stores `self.requested` and `self.available` and calls `super().__init__(f"unknown prompt version '{requested}' (available: {', '.join(available)})")`, so `str(exc) == "unknown prompt version 'v9' (available: v1, v2)"`. Add a module docstring saying it subclasses `ValueError` so a pydantic `field_validator` can raise it.
- [X] T008 Rewrite src/qa_agent/prompt_loader.py (depends on T007): `DEFAULT_PROMPT_VERSION: str = "v2"`; `available_versions() -> list[str]` returns the sorted version names discovered from `prompts/system_*.md` (the part after `system_`, e.g. `"v1"`, `"v2"`; sort by the integer after `v` so `v10` sorts after `v2`); `check_version(version: str) -> None` raises `UnknownPromptVersionError(version, available_versions())` when not available; `render(briefing: str, version: str = DEFAULT_PROMPT_VERSION) -> str` calls `check_version(version)` then returns `template.format(briefing=briefing)` for `prompts/system_<version>.md`; `fingerprint(text: str) -> str` returns `hashlib.sha256(text.encode("utf-8")).hexdigest()`. Update the module docstring: prompts are named files `system_<version>.md`, never edited in place, versions are discovered from the files (adding `system_v3.md` needs no code change), and `fingerprint` identifies a briefing's content on each run (research §3, §5). No `pydantic-ai` import.
- [X] T009 Create src/qa_agent/prompts/system_v2.md as a byte copy of src/qa_agent/prompts/system_v1.md (`cp`), so `render(b)` with the new default works. Stories US1 and US2 then edit only rules 4, 5 and 8 in this file. Do NOT touch system_v1.md.
- [X] T010 Run `pytest tests/contract tests/unit` and `pyright src/`; fix any existing test that called `render(briefing)` and asserted v1 text, by passing `version="v1"` explicitly in that test (the test must still check the same thing). T001 must still pass.

**Checkpoint**: `Outcome` accepts `needs_clarification` everywhere; `render(b, "v1")` and `render(b, "v2")` both work; all existing tests green.

---

## Phase 3: User Story 1 - Agent asks instead of guessing on ambiguous questions (Priority: P1) 🎯 MVP

**Goal**: With prompt v2, an ambiguous question (#49) gets a Portuguese clarifying question with no amounts and outcome `needs_clarification`, which is never downgraded to `none`.

**Independent Test**: `pytest -k test_008_us1` passes (clamp exemption, scripted zero-tool-call clarification, log round-trip, v2 text checks). Live: ask #49 with v2 and check outcome and answer (quickstart §3, SC-001).

### Tests for User Story 1 ⚠️

> Write these first and confirm they FAIL before T015–T017.

- [X] T011 [P] [US1] In tests/unit/qa_agent/test_step_budget.py add `test_008_us1_3_needs_clarification_is_not_downgraded_with_zero_successes` (a `StepBudget` with 0 successes, `_clamp_outcome(reported="needs_clarification", budget=budget) == "needs_clarification"`), `test_008_us1_3_needs_clarification_kept_with_successes` (≥1 success → unchanged), and `test_008_full_and_partial_still_downgraded_with_zero_successes` (edge case: `full`/`partial` with 0 successes → `none`). Build the budget the same way the existing tests at lines ~30–43 do.
- [X] T012 [P] [US1] In tests/unit/qa_agent/test_run_log.py add `test_008_us1_needs_clarification_log_entry_round_trips`: write an `AgentRunLogEntry(outcome="needs_clarification", ...)` with `JsonlRunLogger` to `tmp_path`, read the line back with `AgentRunLogEntry.model_validate_json`, assert equal. Also add `test_008_pre_008_log_line_still_loads`: a literal JSONL line with `"outcome": "partial"` and only the pre-008 fields validates (FR-003).
- [X] T013 [P] [US1] Create tests/contract/qa_agent/test_clarification_outcome.py with `test_008_us1_3_scripted_clarification_with_zero_tool_calls`: use the scripted-model seam used by tests/contract/qa_agent/test_grounded_answers.py (`_answer_with_selection(model_override=...)` with a `FunctionModel`/`TestModel` that returns `AgentAnswer(answer="Você quer saber o valor autorizado, empenhado, liquidado ou pago?", outcome="needs_clarification")` without calling any tool). Assert `result.outcome == "needs_clarification"`, `result.errored is False`, `result.steps == []`. Also add `test_008_us1_agent_answer_accepts_needs_clarification` (`AgentAnswer.model_validate({"answer": "...", "outcome": "needs_clarification"})` succeeds).
- [X] T014 [P] [US1] In tests/unit/qa_agent/test_prompt_loader.py add `test_008_us1_v2_renders_briefing_verbatim` (`b in render(b, "v2")`), `test_008_v2_has_single_briefing_placeholder` (the raw v2 file contains exactly one `{briefing}` and no other `{` or `}`), and `test_008_us1_v2_mentions_needs_clarification_and_outcome_field` (raw v2 text contains `needs_clarification` and `outcome`).

### Implementation for User Story 1

- [X] T015 [US1] In src/qa_agent/capabilities.py make `_clamp_outcome` return `reported` unchanged when `reported == "needs_clarification"`; otherwise keep today's rule (`"none"` when `budget.successes == 0`, else `reported`). Add a docstring with the four-row table from data-model.md "Outcome clamp" and the reason (a clarifying answer makes no data claim; the grader's amount check catches leaked values — research §2). Errored paths keep `outcome="none"`.
- [X] T016 [US1] In src/qa_agent/prompts/system_v2.md replace rule 4 (ambiguity) with the contracts/prompt-v2.md rule 4, in Portuguese: if the question could refer to more than one measure (as the dataset description explains) and the readings give different amounts, don't choose; answer with a clarifying question in Portuguese listing the readings in plain language (e.g. "valor autorizado", "valor empenhado", "valor liquidado", "valor pago"), with no values from the dataset, and report `needs_clarification`; if the wording already names the measure according to the dataset description, answer with that measure without asking; if every reading gives the same amount, answer directly and say the readings agree. No dataset-specific words (no "AEB", no column names). Keep exactly one `{briefing}` and no other braces. Rules 1–3, 6, 7 stay word for word as in v1.
- [X] T017 [US1] In data/briefings/orcamentos-aeb-csv.md add the section "Qual medida a pergunta pede" right after the field dictionary, per contracts/prompt-v2.md "Briefing section" and research §8: (1) a table of wording that names a measure — "gasto", "gastou", "pago", "pagamento", "desembolso" → `pago`; "orçamento previsto", "dotação", "autorizado" → `dotacao_atual`; "empenhado", "empenho" → `empenhado`; "liquidado", "liquidação" → `liquidado`; (2) ambiguous wording: "orçamento", "valor do orçamento" or "recursos" with no qualifier when an amount is asked; the four measures can differ a lot for the same scope (AEB in 2005: autorizado ≈ 206,8 mi, pago ≈ 132,0 mi) — state only *what* is ambiguous, give NO instruction on what to do (that is the prompt's job, keeps the v1 baseline meaningful); (3) counting questions: "quantas ações tiveram execução/gastos em ANO" counts the records for that year whatever the measure values (records with `pago = 0` included); this is not a choice of measure. Then fix the existing synonyms table so it doesn't contradict item 1: remove bare "gasto" from the `empenhado` row if present; keep "gasto empenhado". Change nothing else in the file.

**Checkpoint**: T011–T014 pass. US1 is ready for its live check (#49 under v2).

---

## Phase 4: User Story 2 - Agent reports "none" cleanly when nothing matches (Priority: P1)

**Goal**: With prompt v2, #48 and #50 report `none`, state unavailability, give no substitute item, and no outcome label appears in any answer text.

**Independent Test**: `pytest -k test_008_us2` passes (v2 text checks). Live: ask #48 and #50 with v2 (quickstart §3, SC-001, SC-005).

### Tests for User Story 2 ⚠️

- [X] T018 [P] [US2] In tests/unit/qa_agent/test_prompt_loader.py add `test_008_us2_v2_lists_all_four_outcome_values` (raw v2 text contains each of `full`, `partial`, `none`, `needs_clarification`) and `test_008_us2_v2_carries_over_v1_rules_1_2_3_6_7`: for each of v1's rules 1, 2, 3, 6 and 7, assert the exact v1 rule line appears in v2 (extract the lines from system_v1.md by their rule numbers; FR-006 carry-over).

### Implementation for User Story 2

- [X] T019 [US2] In src/qa_agent/prompts/system_v2.md rewrite rule 5 (coverage) per contracts/prompt-v2.md rule 5, in Portuguese: say plainly when the data doesn't cover the question and invent nothing (v1 wording kept); never give the value, or the name, of a similar or related item as a substitute; if nothing matches, report `none`; if the question is not covered at all (e.g. a period outside the data), report `none` even if it is also ambiguous; if only part is covered, answer that part, declare what is missing and report `partial`. (depends on T016: same file)
- [X] T020 [US2] In src/qa_agent/prompts/system_v2.md replace rule 8 (classification) per contracts/prompt-v2.md rule 8: report the classification only in the `outcome` field of the structured answer; never write it, or any "Classificação:" line, in the answer text; list the four values `full`, `partial`, `none`, `needs_clarification` each with a one-line Portuguese definition matching data-model.md. Keep exactly one `{briefing}` and no other braces. Then run T001, T014 and T018 tests. (depends on T019: same file)

**Checkpoint**: v2 prompt complete (rules 4, 5, 8 changed; others verbatim). US1 + US2 live behavior can be checked.

---

## Phase 5: User Story 3 - Outcome-based automatic grading (Priority: P1)

**Goal**: Records with `expected_outcome` are graded matched/not_matched automatically; records without it are graded exactly as today.

**Independent Test**: `pytest -k test_008_us3` plus the `contains_amount` table, invalid-fixture and SC-007 regrade tests pass without a model.

### Tests for User Story 3 ⚠️

> Write these first and confirm they FAIL before T026–T030.

- [X] T021 [P] [US3] In tests/unit/testset_runner/test_matcher.py add a parametrized `test_008_contains_amount_matches` for `"R$ 42"`, `"R$42.750,00"`, `"R$ -5"`, `"1.234"`, `"12,5"`, `"206.805.295"`, `"0,36"`, `"36%"`, `"12,5 %"` → `True`, and `test_008_contains_amount_ignores` for `"R$"`, `"2005"`, `"em 2005."`, `"2005, 2006"`, `"1. Valor pago"`, `"2) Valor empenhado"`, `"2008 a 2012"`, `"Amazônia-1"`, `"CBERS-3"`, `"por cento"` → `False` (contracts/grading.md table).
- [X] T022 [P] [US3] In tests/unit/testset_runner/test_matcher.py add the grade decision-table tests, all through `DeterministicMatcher().grade(expected, answer, expected_outcome=..., agent_outcome=...)`: `test_008_us3_1_none_expected_none_reported_no_amount_matches` (answer "Não há dados para 2020 sobre o Amazônia-1." → `matched`); `test_008_us3_2_none_expected_partial_reported_not_matched`; `test_008_us3_3_clarification_with_amount_not_matched` (answer contains "R$ 206.805.295" → `not_matched`); `test_008_us3_4_full_expected_checks_outcome_then_number` (`expected="65000"`: outcome `full` with "65.000" → `matched`; outcome `partial` with "65.000" → `not_matched`); `test_008_us3_5_no_expected_outcome_grades_as_before` (re-run every existing case in this file with no keyword args and with `agent_outcome` set to each of the four values and `expected_outcome=None` → same status); `test_008_none_expected_with_agent_outcome_none_value_missing_is_not_matched` (`agent_outcome=None`, `expected_outcome="none"` → `not_matched`); `test_008_full_expected_non_numeric_text` (outcome matches → `needs_review`; outcome differs → `not_matched`); `test_008_expected_text_ignored_for_none_and_clarification` (a numeric `expected` with a no-amount answer and matching outcome → `matched`).
- [X] T023 [P] [US3] In tests/unit/testset_runner/test_loader.py add `test_008_invalid_expected_outcome_is_refused` (loading tests/fixtures/testset_runner/invalid-expected-outcome.json raises `TestsetLoadError`, and the message contains the offending record's location from pydantic), `test_008_expected_outcome_defaults_to_none` (loading mini-testset.json gives `expected_outcome is None` for every record), and `test_008_us3_7_bundled_testset_expected_outcomes` (loading data/testsets/orcamentos-aeb-csv.json: n=48 and n=50 → `"none"`, n=49 → `"needs_clarification"`, the other 47 → `None`).
- [X] T024 [P] [US3] In tests/unit/testset_runner/test_store.py add `test_008_sample_run_fixture_loads` (tests/fixtures/testset_runner/008-sample-run.json and pre-006-run.json load via `JsonFileRunStore`; every `results[].expected_outcome is None`; SC-006) and `test_008_sc007_regrade_is_unchanged`: for every non-errored result in both fixtures, `DeterministicMatcher().grade(r.expected, r.actual_answer) == r.match_status` (SC-007).
- [X] T025 [P] [US3] In tests/contract/testset_runner/test_run_testset.py add end-to-end tests with the existing fake answerer and an in-memory testset: `test_008_us3_expected_outcome_drives_grading` (a record with `expected_outcome="none"` and a fake result `outcome="none"`, answer without amounts → `match_status == "matched"` and `QuestionResult.expected_outcome == "none"`; the same record with fake `outcome="partial"` → `not_matched`), `test_008_us3_6_errored_stays_errored` (`expected_outcome="none"`, fake result `errored=True` → `errored`), and `test_008_expected_outcome_recorded_as_none_when_absent` (FR-018).

### Implementation for User Story 3

- [X] T026 [P] [US3] In src/testset_runner/models.py add `Question.expected_outcome: Outcome | None = None` and `QuestionResult.expected_outcome: Outcome | None = None` (docstring/field description: "the outcome this result was graded against; None when the record had none or the run predates 008"). A value outside `Outcome` must fail validation, which the loader already maps to `TestsetLoadError` (FR-012).
- [X] T027 [US3] In src/testset_runner/matcher.py add module-level `contains_amount(text: str) -> bool` using three compiled patterns `R\$\s*-?\d`, `\d[.,]\d`, `\d\s*%` (true if any matches). Docstring: what each pattern catches, what is deliberately allowed (years, `1.`/`2)` list markers, `Amazônia-1`, `2008 a 2012`), and the known imprecision (`2005,2006` without a space is flagged; a small count written as a plain integer is not caught; text-only, never looks at the dataset) — research §6.
- [X] T028 [US3] In src/testset_runner/matcher.py extend `DeterministicMatcher.grade(self, expected, actual_answer, *, expected_outcome: Outcome | None = None, agent_outcome: Outcome | None = None)` with the ordered rules: (1) `expected_outcome is None` → `self._strategy.evaluate(expected, actual_answer)` exactly as today; (2) `agent_outcome != expected_outcome` → `"not_matched"`; (3) `expected_outcome in ("none", "needs_clarification")` → `"not_matched"` if `contains_amount(actual_answer)` else `"matched"` (ignore `expected`); (4) otherwise → strategy result. Document the table in the docstring. `MatchStrategy` and `NumericMatchStrategy` stay unchanged. No `pydantic-ai` import. (depends on T027)
- [X] T029 [US3] In src/testset_runner/runner.py, where each question is graded: keep `errored` decided first; otherwise call `grader.grade(question.expected, answer_result.answer, expected_outcome=question.expected_outcome, agent_outcome=answer_result.outcome)`; pass `expected_outcome=question.expected_outcome` when building `QuestionResult` (FR-017, FR-018). (depends on T026, T028)
- [X] T030 [US3] Edit data/testsets/orcamentos-aeb-csv.json: add `"expected_outcome": "none"` to n=48 and n=50 and `"expected_outcome": "needs_clarification"` to n=49, placed right after the `"source"` key, keeping the file's 2-space indentation and key order. No other byte changes (verify with `git diff` — only three added lines plus the comma on the preceding `"source"` lines). Do not touch data/testsets/orcamentos-aeb-csv-10.json.

**Checkpoint**: T021–T025 pass. Grading of #48–#50 is automatic; other records unchanged.

---

## Phase 6: User Story 4 - Selectable, recorded prompt version (Priority: P2)

**Goal**: The prompt version is selectable (settings, both CLIs), validated before any question, and each test run records the version and the briefing fingerprint(s); `compare` shows both.

**Independent Test**: `pytest -k "test_008_us4 or test_008_us1_3"` passes; `python -m testset_runner.cli run ... --prompt-version v9` exits 1 with the error line (quickstart §2).

### Tests for User Story 4 ⚠️

> Write these first and confirm they FAIL before T038–T047.

- [X] T031 [P] [US4] In tests/unit/qa_agent/test_prompt_loader.py add `test_008_us4_available_versions` (`== ["v1", "v2"]`), `test_008_us4_default_is_v2`, `test_008_us4_3_check_version_rejects_unknown` (`UnknownPromptVersionError` for `"v9"`, `.requested == "v9"`, `.available == ["v1", "v2"]`, `str(exc) == "unknown prompt version 'v9' (available: v1, v2)"`, and it is a `ValueError`), `test_008_us4_render_v1_equals_v1_template` (`render(b, "v1") == system_v1.md text .format(briefing=b)`), and `test_008_us4_6_fingerprint` (equals `hashlib.sha256(text.encode("utf-8")).hexdigest()`; same text → same value; changed text → different value; non-ASCII text such as "dotação" hashes its UTF-8 bytes).
- [X] T032 [P] [US4] Create tests/unit/qa_agent/test_settings.py with `test_008_us4_1_default_prompt_version_is_v2` (`AgentSettings(model_name="m").prompt_version == "v2"`, with `QA_AGENT_PROMPT_VERSION` unset via `monkeypatch.delenv(..., raising=False)`), `test_008_us4_prompt_version_from_env` (`QA_AGENT_PROMPT_VERSION=v1` → `"v1"`), and `test_008_us4_3_invalid_prompt_version_rejected` (`pydantic.ValidationError` whose message contains `v9` and `v1, v2`).
- [X] T033 [P] [US4] Extend tests/contract/qa_agent/test_clarification_outcome.py (created in T013) with `test_008_us4_3_answerer_rejects_unknown_version` (`QaAgentQuestionAnswerer("m", prompt_version="v9")` raises `UnknownPromptVersionError` before building anything — monkeypatch the selector/logger constructors to fail if called), `test_008_us4_answerer_exposes_resolved_version` (`prompt_version="v1"` → `.prompt_version == "v1"`; no kwarg and env unset → `"v2"`), `test_008_us4_6_result_carries_briefing_fingerprint` (scripted run through `_answer_with_selection`: `result.briefing_fingerprint == fingerprint(selection.briefing)`, also on the agent-exception path), and `test_008_selection_failure_has_no_fingerprint` (dataset-selection failure → `briefing_fingerprint is None`). Also assert via a spy on `prompt_loader.render` that `_answer_with_selection` renders with `settings.prompt_version`.
- [X] T034 [P] [US4] In tests/contract/testset_runner/test_run_testset.py add `test_008_us4_6_run_records_sorted_distinct_fingerprints` (fake answerer returning results with fingerprints `"b"`, `"a"`, `"b"`, `None` → `TestRun.briefing_fingerprints == ["a", "b"]`), `test_008_us4_6_same_briefing_same_fingerprint` (two runs with the same fake briefing text → equal lists; changed text → different lists), `test_008_all_selection_failures_give_empty_list` (`[]`), and `test_008_us4_2_target_prompt_version_persisted` (`TargetConfiguration(..., prompt_version="v1")` is stored and reloaded as `"v1"`).
- [X] T035 [P] [US4] In tests/unit/testset_runner/test_cli.py (existing monkeypatched `run_testset` seam) add `test_008_us4_1_run_defaults_to_v2` (no flag, env unset → the `TargetConfiguration` passed to `run_testset` has `prompt_version == "v2"`), `test_008_us4_2_run_with_v1` (`--prompt-version v1` → `"v1"`), `test_008_us4_3_unknown_version_fails_fast` (`--prompt-version v9` → exit code 1, stderr contains `Error: unknown prompt version 'v9' (available: v1, v2).`, `run_testset` never called, testset loader never called, no file in the runs dir), `test_008_run_summary_prints_version_and_fingerprint` (stdout has `Prompt version: v2` and `Briefing fingerprint: ` + first 12 hex chars; several → comma-separated; `[]` → `none`), and `test_008_us4_4_compare_prints_not_recorded` (compare two copies of tests/fixtures/testset_runner/pre-006-run.json → `prompt_version=not recorded`, `briefing fingerprint: not recorded`, `Briefing fingerprints differ: no`).
- [X] T036 [P] [US4] In tests/unit/testset_runner/test_comparator.py add `test_008_us4_5_comparison_shows_versions_and_fingerprints` (runs with `prompt_version` v1/v2 and fingerprints `["aaa"]`/`["bbb"]` → `run_a.prompt_version == "v1"`, `run_b.prompt_version == "v2"`, `briefing_fingerprints_a/_b` copied, `briefing_fingerprints_differ is True`), `test_008_us4_5_transitions_unchanged` (same result pairs with and without the new fields → identical transition lists and counts), and `test_008_both_none_fingerprints_do_not_differ` (`None`/`None` → `False`).
- [X] T037 [P] [US4] In tests/unit/web_ui/test_cli.py add `test_008_us4_web_ui_accepts_prompt_version` (`--prompt-version v1` reaches the answerer/settings built by the CLI) and `test_008_us4_3_web_ui_unknown_version_fails_fast` (`--prompt-version v9` → exit 1, same stderr error line, port check/bind never called — monkeypatch them).

### Implementation for User Story 4

- [X] T038 [US4] In src/qa_agent/settings.py add `prompt_version: str = DEFAULT_PROMPT_VERSION` to `AgentSettings` (env `QA_AGENT_PROMPT_VERSION`, following the existing `QA_AGENT_` prefix), with a `field_validator("prompt_version")` that calls `prompt_loader.check_version(value)` and returns the value (the raised `UnknownPromptVersionError` is a `ValueError`, so pydantic turns it into a `ValidationError`). Field description: "Prompt version (file prompts/system_<version>.md); default v2".
- [X] T039 [US4] In src/qa_agent/models.py add `QuestionAnsweringResult.briefing_fingerprint: str | None = None` with description "SHA-256 hex of the dataset briefing used; None when dataset selection failed" (research §5).
- [X] T040 [US4] In src/qa_agent/capabilities.py: `_answer_with_selection` renders with `render(selection.briefing, settings.prompt_version)` and passes `briefing_fingerprint=fingerprint(selection.briefing)` to every result it finalizes, including the agent-exception path (add a `briefing_fingerprint: str | None = None` kwarg to `_finalize` and forward it to `QuestionAnsweringResult`). The dataset-selection failure path in `answer_question` leaves it `None`. (depends on T038, T039)
- [X] T041 [US4] In src/qa_agent/answerer.py add keyword-only `prompt_version: str | None = None` to `QaAgentQuestionAnswerer.__init__`: if not `None`, call `check_version(prompt_version)` as the very first statement (before any selector, logger or settings object is built), then pass it into the `AgentSettings(...)` construction; when `None`, let `AgentSettings` resolve it (env, then default). Add a read-only `prompt_version` property returning the resolved `settings.prompt_version`. The `QuestionAnswerer` Protocol is unchanged. (depends on T038)
- [X] T042 [US4] In src/testset_runner/models.py add `TargetConfiguration.prompt_version: str | None = None` ("None = not recorded, run predates 008"), `TestRun.briefing_fingerprints: list[str] | None = None` ("sorted distinct fingerprints of the briefings used; [] if every question failed selection; None = not recorded"), and to `RunComparison` `briefing_fingerprints_a: list[str] | None = None`, `briefing_fingerprints_b: list[str] | None = None`, `briefing_fingerprints_differ: bool = False`.
- [X] T043 [US4] In src/testset_runner/runner.py set `TestRun.briefing_fingerprints = sorted({r.briefing_fingerprint for r in answers if r.briefing_fingerprint})`, where `answers` is the final `QuestionAnsweringResult` of each question (after retries). `target.prompt_version` is persisted as given; `run_testset`'s signature is unchanged. (depends on T039, T042)
- [X] T044 [US4] In src/testset_runner/comparator.py copy `briefing_fingerprints_a/_b` from the two runs and set `briefing_fingerprints_differ = a != b` (so `None`/`None` → `False`). Do not change transition computation or the incompatible-testset check (FR-011). (depends on T042)
- [X] T045 [US4] In src/testset_runner/cli.py: (a) `run` gains `--prompt-version` (default `None`, so `AgentSettings` falls back to `QA_AGENT_PROMPT_VERSION` then v2); build the answerer with `prompt_version=args.prompt_version` BEFORE loading the testset, catch `UnknownPromptVersionError`, print `Error: {exc}.` to stderr and exit 1; build `TargetConfiguration(model_name, base_url, prompt_version=answerer.prompt_version)` (the recorded value is the one actually used); after the run, print `Prompt version: <v>` and `Briefing fingerprint: <first 12 hex chars, comma-separated if several, "none" if []>` ("not recorded" if `None`). (b) `compare` prints per run `Run A: model=… base_url=… prompt_version=<v or not recorded>`, the existing retry-policy line, `  briefing fingerprint: <12-char values or not recorded>`, and after both runs `Briefing fingerprints differ: yes|no` (exact layout in contracts/prompt-version-and-run-record.md). (depends on T041, T043, T044)
- [X] T046 [US4] In src/web_ui/cli.py add `--prompt-version` (default `None`, same env fallback via `AgentSettings`), pass it to `QaAgentQuestionAnswerer(prompt_version=...)`; catch `UnknownPromptVersionError`, print `Error: {exc}.` to stderr and exit 1 before the port check or bind. (depends on T041)
- [X] T047 [US4] Verify src/qa_agent/eval_harness.py needs no code change: it builds `AgentSettings()` (so it reads `QA_AGENT_PROMPT_VERSION`) and records `settings.model_dump()`, which now includes `prompt_version`. If it constructs settings or renders the prompt another way, route it through `AgentSettings.prompt_version`.

**Checkpoint**: T031–T037 pass. `--prompt-version v9` fails fast in both CLIs; runs record version and fingerprint; `compare` shows both.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Full gate, backward-compatibility checks on local data, live acceptance runs and the results record.

- [X] T048 [P] Review docstrings touched by this feature for accuracy against the final code: `_clamp_outcome` (src/qa_agent/capabilities.py), `contains_amount` and `DeterministicMatcher.grade` (src/testset_runner/matcher.py), module docstring of src/qa_agent/prompt_loader.py, `UnknownPromptVersionError` (src/qa_agent/exceptions.py) (Principle III).
- [X] T049 Run the deterministic gate: `pytest tests/contract tests/unit -v` and `pyright src/` — all green, including every `test_008_*` test and T001's v1 pin; `git diff --stat src/qa_agent/prompts/system_v1.md` is empty (quickstart §1).
- [X] T050 Run quickstart §2 by hand: `python -m testset_runner.cli run --testset data/testsets/orcamentos-aeb-csv-10.json --prompt-version v9` and `python -m web_ui.cli --prompt-version v9` → the error line on stderr, exit 1, no run file written, nothing listening.
- [X] T051 Run quickstart §4 (local backward compatibility): every file in data/testset_runs/*.json loads and prints `prompt_version: not recorded` and `regrade diffs: []` for pre-008 runs; every line of data/logs/qa_agent_runs.jsonl validates as `AgentRunLogEntry` (SC-006, SC-007). Record the output for results.md.
- [ ] T052 Run quickstart §3 acceptance runs (requires `QA_AGENT_MODEL=gpt-5.4-nano`, `QA_AGENT_BASE_URL`, `QA_AGENT_API_KEY` in the environment; never commit the key): one full run with `--prompt-version v1` and one with the default (v2) on data/testsets/orcamentos-aeb-csv.json, then `compare V1 V2`, then the quickstart helper script. One run each, strict — no re-runs (Clarification 4). Evaluate SC-001, SC-002, SC-003, SC-004, SC-005, SC-008 against the quickstart table. If any fails, stop and report; the fix is a change to system_v2.md or the briefing followed by a new pair of runs, never a grader change.
- [X] T053 Write specs/008-clarification-outcome/results.md (same shape as specs/007-aggregate-rows-enhancements/results.md): both run IDs, model and base URL, both prompt versions, the briefing fingerprint, the `compare` output summary, and each of SC-001–SC-008 with its measured value and pass/fail, plus the T049/T051 outputs for SC-006/SC-007 (Principle I).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies. T001 MUST run before anything touches `src/qa_agent/prompts/`.
- **Foundational (Phase 2)**: Depends on Setup. BLOCKS all user stories. Order: T004 → T005; T006, T007 in parallel with T004; T008 after T007; T009 after T008; T010 last.
- **US1 (Phase 3)**: Depends on Foundational.
- **US2 (Phase 4)**: Depends on Foundational; its prompt edits (T019, T020) follow T016 because they edit the same file (system_v2.md).
- **US3 (Phase 5)**: Depends on Foundational only (needs `Outcome`). Independent of US1/US2/US4 — can run in parallel with them.
- **US4 (Phase 6)**: Depends on Foundational. T039/T040 touch src/qa_agent/models.py and capabilities.py after US1's T015 (same file); T042/T043 touch src/testset_runner/models.py and runner.py after US3's T026/T029 (same files) if both are in flight.
- **Polish (Phase 7)**: Depends on all stories. T052 needs US1–US4 complete (the acceptance runs need v2 content, graded testset and recorded version).

### User Story Dependencies

- **US1 (P1)**: Foundational only. Unit/contract tests are self-contained; the live check needs US3 grading only to be *measured* automatically.
- **US2 (P1)**: Foundational; shares system_v2.md with US1 (sequential edits).
- **US3 (P1)**: Foundational only.
- **US4 (P2)**: Foundational only. Makes US1–US3 comparable across versions (SC-002, SC-004).

### Within Each User Story

- Tests are written first and must fail before implementation.
- Models before matcher/capabilities, those before runner, runner before CLI.

### Parallel Opportunities

- Setup: T002, T003 in parallel (after or alongside T001).
- Foundational: T006, T007 in parallel with T004.
- US1 tests T011–T014 in parallel (four different files).
- US3 tests T021–T025: T021 and T022 share test_matcher.py (write together or sequentially); T023, T024, T025 in parallel with them. T026 and T027 in parallel (different files).
- US4 tests T031–T037 in parallel (different files; T033 extends the file from T013).
- US3 as a whole can proceed in parallel with US1 + US2.

---

## Parallel Example: User Story 3

```bash
# Tests together (different files):
Task: "T021/T022 contains_amount table + grade decision table in tests/unit/testset_runner/test_matcher.py"
Task: "T023 invalid/bundled expected_outcome in tests/unit/testset_runner/test_loader.py"
Task: "T024 fixture load + SC-007 regrade in tests/unit/testset_runner/test_store.py"
Task: "T025 end-to-end grading in tests/contract/testset_runner/test_run_testset.py"

# Then models and matcher together:
Task: "T026 expected_outcome fields in src/testset_runner/models.py"
Task: "T027 contains_amount in src/testset_runner/matcher.py"
```

## Parallel Example: User Story 4

```bash
Task: "T031 versions/check/fingerprint in tests/unit/qa_agent/test_prompt_loader.py"
Task: "T032 settings in tests/unit/qa_agent/test_settings.py"
Task: "T035 run/compare CLI in tests/unit/testset_runner/test_cli.py"
Task: "T036 comparator in tests/unit/testset_runner/test_comparator.py"
Task: "T037 web UI CLI in tests/unit/web_ui/test_cli.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup (pin v1 first).
2. Phase 2: Foundational.
3. Phase 3: US1 — the agent can ask instead of guessing, and the clarification survives the clamp.
4. **STOP and VALIDATE**: `pytest -k test_008_us1`; optionally ask #49 once with v2 by hand.

### Incremental Delivery

1. Setup + Foundational → `Outcome` widened, loader version-aware, v2 = copy of v1.
2. US1 → ambiguity rule + briefing wording guidance.
3. US2 → coverage and outcome-field rules; v2 prompt complete.
4. US3 → automatic grading of #48–#50 (can be done in parallel with 2–3).
5. US4 → version selection and run record; enables the v1-vs-v2 comparison.
6. Polish → gate, local backward-compat checks, one v1 + one v2 run, results.md.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks.
- Commit after each task or logical group.
- Stop at any checkpoint to validate a story on its own.
- `data/testset_runs/` and `data/logs/` are gitignored: T002 copies from the local run file into a committed fixture; T051/T052 are local checks.
