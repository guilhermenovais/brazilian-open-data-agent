# Contract: Failure Translation

Every technical failure this feature can encounter is translated at one of three points —
never propagated past `answer_question` (research.md §10). Nothing in this table is ever
shown to the user verbatim; the "User-facing effect" column describes the *shape* of the
Portuguese response, not fixed copy.

| Failure | Raised by | Caught by | Tier | User-facing effect |
|---------|-----------|-----------|------|---------------------|
| `NoBriefingsAvailableError` | `StaticDatasetSelector.select` (via `select_dataset`) | `answer_question`, before any `Agent` is built | 1 | Fixed Portuguese "cannot determine a dataset" answer, `outcome="none"`, no model call made. |
| `DatasetNotFoundError` | `LocalDatasetLocator.locate` (via `select_dataset`) | `answer_question`, before any `Agent` is built | 1 | Same as above. |
| `BriefingNotFoundError` | `FileBriefingSource.get` (via `select_dataset`) | `answer_question`, before any `Agent` is built | 1 | Same as above. |
| `DataSourceNotFoundError` | `data_access.capabilities.*` (inside a tool wrapper) | The tool wrapper → `pydantic_ai.ModelRetry` | 2 | None directly — the model sees the retry message, may adjust and retry (within the step budget), and still produces a normal final answer. |
| `UnreadableSourceError` | `data_access.capabilities.*` | Tool wrapper → `ModelRetry` | 2 | Same as above — the model is expected to recognize this source is unusable and either try a different source or state, in its final Portuguese answer, that this part of the data couldn't be read (User Story 4 AS1), without repeating the raw error. |
| `FieldNotFoundError` | `data_access.capabilities.*` | Tool wrapper → `ModelRetry` | 2 | Same — typically recoverable by re-inspecting the schema and retrying with a valid field name. |
| `NumericTypeError` | `data_access.capabilities.*` | Tool wrapper → `ModelRetry` | 2 | Same — recoverable by not treating that field as numeric. |
| `IdentifierCollisionError` | `data_access.dataset.Dataset` (surfaces through any capability call) | Tool wrapper → `ModelRetry` | 2 | Same. |
| Step budget exhausted (not an exception) | `step_budget.try_reserve()` returning `False` | The tool wrapper returns `BudgetExhausted` directly (no exception at all) | — | None directly — nudges the model to finalize; if `successes > 0` the model produces a real partial answer (FR-012/FR-007), else the deterministic clamp (data-model.md §5) forces `outcome="none"`. |
| `pydantic_ai.exceptions.UnexpectedModelBehavior` | `agent.run(...)` | `answer_question`, around the `agent.run()` call | 3 | Fixed Portuguese "could not process the question right now" answer, `outcome="none"`. No partial-answer attempt (research.md §10 — no trustworthy synthesis step ran). |
| Model provider HTTP/network/timeout error | `agent.run(...)` (raised by the underlying provider SDK) | `answer_question`, around the `agent.run()` call | 3 | Same as above. |
| Any other exception escaping `agent.run(...)` | `agent.run(...)` | `answer_question`, around the `agent.run()` call | 3 | Same as above — a catch-all, not an enumerated allowlist, since FR-009 requires *every* technical failure to be translated, not only anticipated ones. |

## Design note: why Tier 2 messages may name identifiers but Tier 1/3 answers never do

A `ModelRetry` message is conversation context fed back to the *model*, not the end user —
the model needs the offending field/identifier to self-correct (research.md §4). The system
prompt instructs the model to never repeat such internal detail in its final `answer`
field, which is the only thing `QuestionAnsweringResult`/`AgentRunLogEntry` ever exposes
downstream. Tier 1 and Tier 3 fallback messages are fixed strings composed entirely by
`qa_agent`'s own code (never derived from the caught exception's text), so there is no path
by which raw error content reaches the user in those tiers either.
