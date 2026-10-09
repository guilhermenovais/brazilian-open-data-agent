# Contract: Scripted conversation test set and `run_conversations`

Models: [data-model.md](../data-model.md) (`ScriptedTurn` … `ConversationRun`). Rationale:
[research.md](../research.md) R9–R11.

## File format

`data/testsets/conversations/orcamentos-aeb-csv-conversations.json`: a JSON array.

```json
[
  {
    "id": "follow-up-year-01",
    "category": "follow-up-year",
    "description": "Muda apenas o ano após uma pergunta sobre valor pago.",
    "turns": [
      {"message": "Quanto foi pago pela AEB em 2015?", "expected": "<computed>", "source": "dados_gerais/tb_geral.csv", "scored": false},
      {"message": "e em 2016?",                          "expected": "<computed>", "source": "dados_gerais/tb_geral.csv"}
    ]
  },
  {
    "id": "fresh-chat-follow-up-01",
    "category": "fresh-chat-follow-up",
    "turns": [{"message": "e em 2016?", "expected_outcome": "none"}]
  }
]
```

`<computed>` values are filled in during implementation by a deterministic pandas query over
the listed `source`, never by hand-reading or model output.

### Loader rules (`ConversationTestsetLoader.load`)

Raise `TestsetLoadError` (the existing exception) when:

- the file is unreadable or not valid JSON
- any record fails model validation (empty `turns`, empty `message`, bad `expected_outcome`, …)
- `id`s are duplicated
- a turn has `scored: true` but neither `expected` nor `expected_outcome`

`content_hash` is the sha256 of the raw bytes.

### Scoring convention: only the measured turn is scored

A category's match rate in `by_category` is read directly as the success criterion it
measures. So in every conversation, **only the turn(s) the criterion measures are scored**.
Every context turn (the first question before a follow-up, the vague question before a
clarification reply, the unrelated turns before a standalone question) sets
`"scored": false`. It may still carry `expected` / `expected_outcome` for documentation,
and the value is copied into the `TurnResult`, but it does not count toward the rate. A
failed context turn therefore cannot raise or lower the measured criterion. Its status is
`unscored` (or `errored`), and its `actual_answer` and `ungrounded_figures` stay in the run
file for review.

### Required coverage (FR-015)

| Category | Min. conversations | Scored turn(s) | Measures |
|---|---|---|---|
| `follow-up-year` | 3 | the last turn only | SC-001 |
| `follow-up-metric` | 3 | the last turn only | SC-001 |
| `follow-up-reference` | 3 | the last turn only | SC-001 |
| `clarification` | 3 | the reply turn only (vague first turn `scored: false`) | SC-002 |
| `clarification-insufficient` | 1 | the still-underspecified reply turn (`expected_outcome: "none"`) | US2-AS2 |
| `clarification-ignored` | 1 | the unrelated complete question | US2-AS3 |
| `standalone-after-unrelated` | 2 | the standalone turn only | SC-004 |
| `fresh-chat-follow-up` | 2 | the single turn (`expected_outcome: "none"`) | SC-005 |
| `long-conversation` | 1 (≥ 20 turns) | none required (all may be `scored: false`) | SC-006: no turn `errored`, and at the default limit `history_turns_used == history_turns_sent` on every turn (FR-011) |

The `clarification` category holds only exchanges where the reply completes the question,
so its rate is exactly SC-002's "correct answer to the completed question". The
still-underspecified case (US2-AS2) lives in `clarification-insufficient` so that its
expected decline does not mix into SC-002.

## `run_conversations`

```python
def run_conversations(
    testset_path: str | Path,
    target: TargetConfiguration,
    *,
    answerer: ConversationalAnswerer,
    store: ConversationRunStore,
    history_char_limit: int,
    prompt_version: str = CONVERSATION_PROMPT_VERSION,
    matcher: MatchStrategy = NumericMatchStrategy(),
    retry_policy: RetryPolicy = RetryPolicy(),
    sleep: Callable[[float], None] = time.sleep,
) -> ConversationRun
```

1. Load the test set. `TestsetLoadError` propagates and nothing is saved.
2. Generate `run_id` up front. For each conversation, start with `history = []`. For each
   turn *k*:
   - `context = ConversationContext(conversation_id=f"{run_id}:{conv.id}", turn_index=k, history=list(history))`
   - `result, attempts, failed = _ask_with_retry(lambda: answerer.answer_turn(turn.message, context), retry_policy, sleep)`
   - `history_turns_used = len(fit_history(context.history, history_char_limit))`. This is the
     same pure function `answer_turn` applies, so it equals what the model received as long
     as `history_char_limit` equals the answerer's limit (see below).
   - `history.append(ConversationTurn(question=turn.message, answer=result.answer))`. The
     actual answer is appended even when the turn errored, as the UI would show it.
   - Score (below) and record `TurnResult`.
3. Summarize, build the `ConversationRun`, `store.save(run)`, and return it.

`history_char_limit` must equal the answerer's configured limit. The CLI builds both from
the same value, and the run records it.

### Turn scoring

```text
if result.errored:                              status = "errored"
elif not turn is scored:                        status = "unscored"
else:
    grades = []
    if expected is not None:         grades.append(matcher.evaluate(expected, answer))
    if expected_outcome is not None: grades.append("matched" if agent_outcome == expected_outcome else "not_matched")
    status = worst(grades)   # not_matched < needs_review < matched
```

`ungrounded_figures = grounding.ungrounded_figures(answer, turn.message, result.steps)` is
computed for every non-errored turn. It is **reported, not scored**.

### Resolving flagged figures (SC-003)

The screen has known false positives (e.g. a difference between two retrieved sums), so
each flagged figure gets a recorded verdict instead of an unrecorded judgement. For every
figure in every non-empty `ungrounded_figures` list of a run cited as evidence, the results
note (`results.md`) records one row: `run_id`, scripted conversation `id`, `turn_index`,
the figure, the verdict, and the reason. The verdict is one of:

- `derived`: the figure is computed deterministically from values in the **same turn's**
  `steps[].result_summary` (the reason names those values and the operation, so anyone can
  recheck it against the run file);
- `ungrounded`: anything else, including a value that appears only in an earlier answer.

SC-003 is met for a run when it has **zero `ungrounded` verdicts**. Since the run file
holds the answer and the current turn's steps, every verdict can be re-verified from the
saved run alone (Principle I).

### `grounding.ungrounded_figures`

```python
def ungrounded_figures(answer: str, message: str, steps: list[RetrievalStep]) -> list[str]
```

This returns the numeric substrings of `answer`, as the matcher's regex finds them, whose
`parse_locale_number` value does not equal any value parsed from the numeric substrings of
`message` or of any `step.result_summary`. Unparseable substrings are ignored. The order
of first appearance is kept and duplicates are removed.

### Summary

The summary follows `ConversationRunSummary` in data-model.md. `by_category` is keyed by
`ScriptedConversation.category`. `target_unreachable` is true when there is at least one
turn with `dataset_key != "<none>"` and every such turn is `errored`.

### Store

`JsonFileConversationRunStore(out_dir)` has `save(run) -> str`, which writes
`<out_dir>/<run_id>.json` with indent 2, and `load(path) -> ConversationRun`, which raises
`RunLoadError` on read or validation failure. It mirrors `JsonFileRunStore`.

## Guarantees

- `run_testset` behavior, its run files and its CLI output are unchanged (FR-014). The
  `_ask_with_retry` refactor is covered by the existing `test_retry.py`.
- Conversations never share history (SC-005). Every turn gets a fresh
  `answer_turn` call and thus a fresh step budget (FR-009).
