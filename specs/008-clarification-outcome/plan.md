# Implementation Plan: Clarification Outcome, Prompt v2 and Outcome-Based Grading

**Branch**: `008-clarification-outcome` | **Date**: 2026-09-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-clarification-outcome/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Three connected changes fix the guessing and mislabelling seen in run
`20260924T121028315459Z` (#48–#50). They also make the fix measurable.

1. **Fourth outcome.** A shared `Outcome` alias
   (`full | partial | none | needs_clarification`) replaces the five written-out literals in
   `qa_agent` and `testset_runner`. `_clamp_outcome` never downgrades `needs_clarification`.
   Widening the literal keeps every stored run and log loadable (research §1–§2).
2. **Prompt v2, selectable and recorded.** `system_v2.md` sits next to the untouched
   `system_v1.md`.
   - Versions are discovered from the prompt files.
   - `AgentSettings.prompt_version` defaults to v2 and is validated.
   - `--prompt-version` is added to both CLIs.
   - The run records the version on `TargetConfiguration` and the sorted distinct briefing
     SHA-256 fingerprints on `TestRun`. Each answer carries its fingerprint back.
   - The `orcamentos-aeb-csv` briefing gains a "which wording selects which measure" section.

   See research §3–§5, §8–§10.
3. **Outcome-based grading.**
   - Testset records gain an optional `expected_outcome`.
   - `DeterministicMatcher.grade` gains keyword-only `expected_outcome`/`agent_outcome`.
     When an expected outcome is set, the outcomes must be equal. For `none` and
     `needs_clarification`, the answer must also contain no amount: `R$ n`, `n.n`/`n,n`, or
     `n%`.
   - Records without an expected outcome are graded exactly as today.
   - #48 and #50 are set to `none`, #49 to `needs_clarification`.

   See research §6–§7.

Acceptance is measured with one v1 run and one v2 run on the edited testset, plus
`compare`, as described in [quickstart.md](./quickstart.md). The results go in `results.md`.

## Technical Context

**Language/Version**: Python 3.11+ (venv 3.12)

**Primary Dependencies**:
- `pydantic` v2 and `pydantic-settings`: `AgentSettings` validator
- `pydantic-ai`: structured `output_type`, unchanged wiring
- `pandas`: untouched

No new dependency. `hashlib` and `re` are from the standard library.

**Storage**: JSON run files (`data/testset_runs/`, gitignored), JSONL logs (`data/logs/`,
gitignored), and versioned artifacts in git (prompts, briefing, testset). All model changes
are optional or widening, so no migration is needed.

**Testing**: pytest + pyright (CI: `pytest tests/contract tests/unit`, `pyright src/`).
Grading, loading, clamp, prompt-loader and CLI behavior are tested without a model. Agent
paths use the existing scripted-model seam (`_answer_with_selection(model_override=...)`).
The model-quality criteria (SC-001–SC-005, SC-008) are live-run checks outside CI, as with
the 003 harness and the 006/007 results.

**Target Platform**: Linux, local Python process (library, CLIs, local web UI).

**Project Type**: Single-project Python library (`src/` layout) with two CLIs.

**Performance Goals**: None beyond the current behavior. The extra work per answer is one
SHA-256 of a ~10 KB briefing, and grading adds three regex scans.

**Constraints**:
- `system_v1.md` must stay byte-identical (FR-005).
- Stored runs and logs must load unchanged (FR-003).
- Grading for records without an expected outcome must not change (FR-016).
- Grading must be pure and model-free (FR-020).
- Dataset-specific wording stays in the briefing (Principle V).
- Acceptance is judged on one run of each version, strictly (Clarification 4).

**Scale/Scope**:
- `qa_agent`: `models`, `settings`, `prompt_loader`, `capabilities`, `answerer`, a new
  `exceptions` module and a new `prompts/system_v2.md`.
- `testset_runner`: `models`, `matcher`, `runner`, `comparator`, `cli`.
- `web_ui`: `cli` (one flag).
- Data: `data/briefings/orcamentos-aeb-csv.md` and `data/testsets/orcamentos-aeb-csv.json`
  (three records).
- Tests: new and extended unit and contract tests, one new trimmed run fixture.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|-----------|------------|
| I. Reproducibility | Each run records the prompt version (`target.prompt_version`) and briefing fingerprint(s), so a run's prompt and briefing are always identifiable. The v1/v2 claim comes from two recorded runs plus `compare`, written up in `results.md` (research §11). **Pass.** |
| II. Evidence Before Implementation | Every change traces to an observation recorded in the spec's Evidence section: #49 guess → rule 4; #48 substitute → rule 5; #48/#50 labels → rule 8; `needs_review` blind spot → grading. **Pass.** |
| III. Documentation | Research, data model, three contracts, quickstart and `results.md` (carried into tasks). The prompt and briefing changes are themselves documented artifacts. Docstrings are updated for the matcher (the amount rule and its known imprecision), the clamp, and `prompt_loader`. **Pass.** |
| IV. Tests Document Behavior | One test per acceptance scenario, named `test_008_us<N>_<M>_...`, plus named edge-case tests (the `contains_amount` table, invalid expected outcome, SC-007 regrade). **Pass.** |
| V. Mechanism vs Domain Knowledge | The wording-to-measure mapping lives in the briefing. The prompt carries only the general "ask when readings differ" rule. The grader knows outcomes and amount shapes, never dataset fields. Prompt versions are discovered from files, not listed in code. **Pass.** |
| VI. Deterministic Over Model Judgment | Grading of expected outcomes is mechanical (equal outcomes plus regex). Deciding whether a question is ambiguous stays a model judgment, which is the kind of call the principle reserves for the model. **Pass.** |
| VII. Simplicity | One alias, one exception type, keyword-only extensions of existing signatures, no new Protocol and no new dependency. The fingerprint is a list only because the runner can't assume one dataset per run; no conflict rules are needed (research §5). **Pass.** |
| VIII. Security | `TargetConfiguration` still carries no credential. `fingerprint` hashes only public briefing text. **Pass.** |
| IX. CI Gate | All new deterministic behavior is inside the existing pytest + pyright CI. The live acceptance runs are outside CI by design (as in 003/006/007) and recorded in `results.md`. **Pass.** |
| X. Usage as Research Data | The run log accepts the new outcome, so clarification requests are now visible in usage data instead of being folded into `none`. Recording the version in the run log is out of scope (spec Assumptions). **Pass.** |
| Eng. 1 (thin wiring) | The grading, fingerprint, version discovery and clamp logic are plain Python with no `pydantic-ai` import in `matcher`/`prompt_loader`. **Pass.** |
| Eng. 2 (interfaces) | The `MatchStrategy` and `QuestionAnswerer` Protocols are unchanged. New prompt versions are added by adding a file. **Pass.** |
| Eng. 3 (polymorphic dispatch) | N/A. The grading rules are an ordered decision table, not format or backend dispatch. |
| Eng. 4 (DI over globals) | The version flows through `AgentSettings`, which is injected per answerer. There is no module global. **Pass.** |
| Eng. 5 (validated boundary) | `Outcome` is enforced on `AgentAnswer` (model output), testset records and stored results. An invalid version is rejected at settings construction. **Pass.** |
| Eng. 6 (testable without a model) | `grade`, `contains_amount`, `_clamp_outcome`, `prompt_loader` and the CLIs are all tested directly. **Pass.** |
| Eng. 7 (typed settings) | `prompt_version` is a typed, validated `AgentSettings` field with env fallback. The harness records it through `settings.model_dump()`. **Pass.** |
| Eng. 8 (versioned prompts/briefings) | Prompts: v2 is a new named file, v1 is pinned by a hash test, and the version is referenced by each run. **Briefing: edited in place, which departs from "never edited in place"** (see Complexity Tracking). **Justified exception.** |
| Eng. 9 (native instrumentation) | Unchanged. **Pass.** |
| Eng. 10 (static typing) | The `Outcome` alias makes a missed literal site a pyright error. Full hints throughout. **Pass.** |

**Gate result (pre-research)**: **Pass**, with one justified exception (Eng. 8, briefing),
recorded below.

**Post-design re-check (after Phase 1)**: still **Pass**. Design produced no new
violations. Two risks were found and handled in the design rather than deferred:

- The #28/#29 counting-question regression risk for SC-003/SC-004 is addressed by the
  briefing's "counting is not a choice of measure" bullet (research §8).
- Run files are gitignored, so SC-006/SC-007 CI coverage uses a committed trimmed fixture,
  with the full check in quickstart §4 (research §11).

## Project Structure

### Documentation (this feature)

```text
specs/008-clarification-outcome/
├── plan.md                                   # This file
├── research.md                               # Phase 0
├── data-model.md                             # Phase 1
├── quickstart.md                             # Phase 1
├── contracts/
│   ├── prompt-v2.md                          # system_v2.md rules + briefing section (FR-005–007)
│   ├── prompt-version-and-run-record.md      # selection, validation, fingerprint, CLIs, compat (FR-001–004, 008–011)
│   └── grading.md                            # outcome-aware grade + contains_amount (FR-012–020)
├── results.md                                # after the acceptance runs (implementation phase)
└── tasks.md                                  # Phase 2 (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
src/
├── qa_agent/
│   ├── models.py            # Outcome alias; AgentAnswer/QuestionAnsweringResult/AgentRunLogEntry use it;
│   │                        #   QuestionAnsweringResult.briefing_fingerprint
│   ├── exceptions.py        # NEW: UnknownPromptVersionError(ValueError)
│   ├── prompt_loader.py     # DEFAULT_PROMPT_VERSION, available_versions, check_version, render(b, version), fingerprint
│   ├── prompts/
│   │   ├── system_v1.md     # UNCHANGED (hash-pinned)
│   │   └── system_v2.md     # NEW
│   ├── settings.py          # prompt_version field + validator
│   ├── capabilities.py      # render with settings.prompt_version; set briefing_fingerprint; clamp exemption
│   └── answerer.py          # prompt_version kwarg (checked first) + property
├── testset_runner/
│   ├── models.py            # Question.expected_outcome; QuestionResult.agent_outcome/expected_outcome;
│   │                        #   TargetConfiguration.prompt_version; TestRun.briefing_fingerprints;
│   │                        #   RunComparison.briefing_fingerprints_a/_b/_differ
│   ├── matcher.py           # contains_amount; DeterministicMatcher.grade(..., expected_outcome, agent_outcome)
│   ├── runner.py            # pass outcomes to grade; store expected_outcome; derive briefing_fingerprints
│   ├── comparator.py        # copy fingerprints + differ flag (transitions unchanged)
│   └── cli.py               # --prompt-version; print version/fingerprint in run + compare
└── web_ui/
    └── cli.py               # --prompt-version; fail fast on unknown version

data/
├── briefings/orcamentos-aeb-csv.md           # + "Qual medida a pergunta pede" section
└── testsets/orcamentos-aeb-csv.json          # #48/#50 → none, #49 → needs_clarification

tests/
├── unit/qa_agent/test_prompt_loader.py       # v1 hash pin, versions, check_version, fingerprint, render(v2)
├── unit/qa_agent/test_step_budget.py         # clamp exemption (US1-3)
├── unit/qa_agent/test_run_log.py             # needs_clarification round-trip
├── unit/qa_agent/test_settings.py            # NEW: default v2, env, invalid version
├── unit/testset_runner/test_matcher.py       # contains_amount table; grade decision table (US3-1..6)
├── unit/testset_runner/test_loader.py        # expected_outcome valid/invalid; bundled testset (US3-7)
├── unit/testset_runner/test_store.py         # old runs load with None fields; SC-007 regrade on fixtures
├── unit/testset_runner/test_cli.py           # --prompt-version, v9 fail-fast, printed version/fingerprint
├── unit/testset_runner/test_comparator.py    # fingerprints shown, differ flag, transitions unchanged
├── unit/web_ui/test_cli.py                   # --prompt-version, v9 fail-fast
├── contract/qa_agent/                        # scripted needs_clarification with 0 tool calls; fingerprint on result
├── contract/testset_runner/test_run_testset.py  # expected_outcome grading end-to-end with fake answerer
└── fixtures/testset_runner/
    ├── 008-sample-run.json                   # NEW: trimmed copy of run 20260924T121028315459Z (incl. #48–#50)
    └── invalid-expected-outcome.json         # NEW
```

**Structure Decision**: The same single-project `src/` layout as features 001–007. Logic
stays in the framework-free modules (`matcher`, `prompt_loader`, `capabilities` helpers).
The CLIs only add a flag and print lines.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Eng. 8: `data/briefings/orcamentos-aeb-csv.md` is edited in place instead of being added as a new named version | Clarification 3 chose this. Briefing selection and naming infrastructure doesn't exist, and building it is out of scope for fixing three observed failures. Each run's SHA-256 briefing fingerprint makes the briefing it used identifiable, and the text stays diffable in git history. | A versioned briefing (`orcamentos-aeb-csv-v2.md` plus a briefing-version setting) needs new selection plumbing in `dataset_selector` and a second setting to record. That is speculative generality ahead of need (Principle VII). The fingerprint meets the principle's goal: every run references exactly the briefing content it used. |
