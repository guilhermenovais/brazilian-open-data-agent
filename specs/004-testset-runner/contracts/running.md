# Contract: Running a Testset

```python
def run_testset(
    testset_path: str | Path,
    target: TargetConfiguration,
    *,
    answerer: QuestionAnswerer,
    matcher: MatchStrategy = NumericMatchStrategy(),
    store: RunStore,
) -> TestRun: ...
```

The one public entry point of `testset_runner` for User Story 1. A CLI (`cli.py run`) is the
only caller in this feature; the function itself has no I/O dependency beyond what's injected.

## Input

- `testset_path: str | Path` — path to a testset JSON file structured like
  `data/testsets/orcamentos-aeb-csv.json` (FR-001). Not required to be that exact file — any
  file matching `Question`'s schema (data-model.md) is accepted.
- `target: TargetConfiguration` — `model_name` and optional `base_url` for this run (FR-002).
  Never carries credentials (data-model.md).
- `answerer: QuestionAnswerer` — injected (Engineering Principle 4); production callers pass a
  `QaAgentQuestionAnswerer` built from `target` (contract: `answering.md` from
  `003-qa-agent-workflow`, extended per this feature's `data-model.md`); tests inject a fake.
- `matcher: MatchStrategy` — injected, defaults to the one shipped `NumericMatchStrategy`
  wrapped in `DeterministicMatcher` (research.md §5). Present as a parameter, not a hardcoded
  call, specifically so a future strategy is a substitution, not an edit to this function.
- `store: RunStore` — injected persistence (research.md §7).

## Output

`TestRun` (data-model.md) — the complete, persisted record: testset identity, target
configuration, one `QuestionResult` per question, and a `RunSummary`. The same object is both
returned and (as a side effect) written to disk via `store.save`.

## Side effects

Exactly one `TestRun` file is written via `store.save(...)`, after every question has been
processed — never incrementally (research.md §7). No file is written if `TestsetLoader.load`
fails before any question is asked.

## Isolation guarantee

Every `Question` in the run is answered by exactly one `answerer.answer(question.question)`
call; nothing computed for one question (its `QuestionResult`, or anything internal to how
`answerer` produced it) is passed as input to any other question's call (FR-003, SC-004 —
research.md §2).

## Never raises for a single question's failure

A single question's `errored=True` result (dataset selection failed, or the model call itself
failed) is recorded as `match_status="errored"` and the loop continues (FR-004). The only
exceptions `run_testset` itself can raise are pre-loop, whole-run failures:

## Raises

| Exception            | When |
|-----------------------|------|
| `TestsetLoadError`     | `testset_path` doesn't exist, isn't readable, isn't valid JSON, or any record is missing `n`/`question`/`expected`, or `n` is duplicated within the file (FR-013). Raised before `answerer.answer` is called for any question — no partial report is ever produced for this case. |

## Behavioral requirements (traceability)

| Scenario / Requirement | Behavior |
|-------------------------|----------|
| US1 AS1 (full run, one report) | Every `Question` in `testset.questions` produces exactly one `QuestionResult`, in the same order, inside one returned/persisted `TestRun`. |
| US1 AS2 (per-question detail) | Each `QuestionResult` carries `question`, `expected`, `actual_answer`, `agent_outcome`, `dataset_key`, `steps`, and `match_status` — sufficient to explain any single result without re-running anything (SC-002). |
| US1 AS3 (numeric auto-grade) | `expected` parses via `data_access.numeric.parse_locale_number` (after stripping a leading `~`) → `match_status` is `"matched"`/`"not_matched"`, never `"needs_review"`. |
| US1 AS4 (non-numeric → human review) | `expected` does not parse as a number → `match_status` is always `"needs_review"` (never auto-guessed) unless the question itself `errored`. |
| US1 AS5 (one question errors, run continues) | `errored=True` for that question → `match_status="errored"` for that row only; every other question in the run still gets processed and a full `TestRun` with all `total_questions` rows is still produced. |
| FR-012 (full bundled sample) | `run_testset("data/testsets/orcamentos-aeb-csv.json", ...)` produces a `TestRun` with `len(results) == 50`. |
| FR-013 (fail fast) | See "Raises" above. |
| Edge Case (target unreachable for whole run) | `RunSummary.target_unreachable=True` when every non-`errored`-ineligible question came back `errored` (research.md §6) — a single run-level fact, not 50 individually confusing rows. |
