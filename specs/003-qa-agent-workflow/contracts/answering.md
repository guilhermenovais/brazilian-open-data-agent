# Contract: Answering a Question

```python
def answer_question(
    question: str,
    *,
    selector: DatasetSelector,
    selection_logger: SelectionLogger,
    run_logger: RunLogger,
    settings: AgentSettings,
) -> QuestionAnsweringResult: ...
```

The one public entry point of `qa_agent`. A future CLI/API surface calls this directly; no
other function in this package is meant to be called from outside it.

## Input

- `question: str` — Portuguese natural-language text, exactly as received (FR-001). Not
  validated for language or well-formedness — the spec's Assumptions place that out of
  scope. Empty/whitespace-only input is not specially handled here: it is passed through to
  `select_dataset` and then to the model like any other question and answered per the normal
  "too vague to map to any concrete data" edge case (spec Edge Cases), not rejected upfront.
- `selector: DatasetSelector` — injected selection strategy, passed straight through to
  `dataset_selector.capabilities.select_dataset` (data-model.md, state/control flow §1).
- `selection_logger: SelectionLogger` — injected, passed straight through to
  `select_dataset` (the existing `002-dataset-selector` log — unaffected by this feature).
- `run_logger: RunLogger` — injected, this feature's own FR-013 recorder (data-model.md).
- `settings: AgentSettings` — `model_name` (required) and `instrument` (data-model.md);
  `answer_question` builds the `Agent` from these on every call rather than caching one
  globally (Engineering Principle 4 — no module-level global agent).

## Output

`QuestionAnsweringResult` (data-model.md): `answer` (Portuguese, the only field meant for the
end user), `dataset_key`, and `outcome` — the latter two exist for observability/testing, not
for the end user to see directly.

## Side effects

Exactly one `AgentRunLogEntry` is written via `run_logger.log(...)` per call — on every
outcome, including `"none"` (data-model.md §"State / control flow"). This is in addition to,
never a replacement for, the `DatasetSelectionLogEntry` that `select_dataset` itself writes
via `selection_logger` on its own successful calls (unchanged from `002`).

## Never raises

`answer_question` does not propagate `DatasetSelector*` exceptions, `DataAccessError`
subclasses, or `pydantic_ai` exceptions to its caller — every reachable failure is caught and
translated into a `QuestionAnsweringResult` with a Portuguese `answer` and `outcome="none"`
(research.md §10; see `errors.md` for the full translation table). A caller of
`answer_question` never needs a `try`/`except` around it for any condition this feature's
spec anticipates.

## Behavioral requirements (traceability)

| Scenario / Requirement | Behavior |
|-------------------------|----------|
| US1 AS1 (grounded answer) | Question fully within coverage → `outcome="full"`, `answer` states the retrieved value(s) in Portuguese, matching the underlying data exactly. |
| US1 AS2 (everyday synonym) | A synonym like "gasto" for "empenhado" → resolved via the briefing's documented synonyms (FR-010); same correct field, same `outcome="full"`. |
| US1 AS3 (no internal details leak) | `answer` never contains a file name, column name, or dataset identifier, regardless of outcome. |
| US2 AS1–AS3 (out of coverage) | Wrong subject / out-of-range year / untracked granularity → `outcome="none"`, `answer` states plainly, in Portuguese, that the data doesn't cover the question — no invented figure. |
| US2 AS4 (partially covered) | One of two requested facts is covered → `outcome="partial"`, `answer` gives the covered fact and explicitly names, in Portuguese, what couldn't be answered and why. |
| US3 AS1–AS3 (multi-step) | Filter+aggregate / ranking / structure-then-filter questions → the model performs the necessary tool-call sequence itself (`tools.md`); `answer` reflects the correctly computed result, not a partial/unsorted sample. |
| US4 AS1–AS2 (technical failure) | Any Tier 1/2/3 failure (research.md §10) → `answer` is a plain Portuguese explanation with zero raw error text/paths/identifiers; a Tier 1/3 failure never presents a guessed result as complete. |
| FR-011 (independent requests) | No parameter or module-level state carries information from one `answer_question` call into the next; every call builds a fresh `AgentDeps`/`StepBudget`. |
| FR-012 (10-step bound) | See `tools.md` for the exact enforcement point; `outcome="partial"`/`"none"` per whether any facts were retrieved before the bound (data-model.md, research.md §3/§5). |
| FR-013 (usage log) | Exactly one `AgentRunLogEntry` per call, on every path, per "Side effects" above. |
