# Data Model: Conversational Context in the Web UI Chat

Phase 1 output for [plan.md](./plan.md). All models are pydantic v2 `BaseModel`s unless
stated otherwise. "Optional, default None" additions keep older persisted files and log
lines valid.

## qa_agent (`qa_agent/conversation.py`, no `pydantic_ai` import)

### ConversationTurn

One earlier, visible exchange in a chat (spec entity **Turn**, text only per FR-001).

| Field | Type | Rules |
|---|---|---|
| `question` | `str` | `min_length=1`. The user's message text, stripped. |
| `answer` | `str \| None` | The agent's final visible reply text. `None` when the turn has no reply (e.g. the request ended in an `ErrorChunk`). Never contains tool calls or results. |

Derived: `size = len(question) + len(answer or "")`, used by `fit_history`.

### ConversationContext

Everything `answer_turn` needs besides the current message.

| Field | Type | Rules |
|---|---|---|
| `conversation_id` | `str` | `min_length=1`. The web UI chat `id`, or `"<run_id>:<conversation id>"` in the runner. |
| `turn_index` | `int` | `≥ 1`. Position of the current message in the conversation. It equals `len(history) + 1` before trimming, because trimming never renumbers. |
| `history` | `list[ConversationTurn]` | Oldest first. Full, untrimmed. Trimming happens inside `answer_turn`. Empty for a new chat (FR-008). |

### fit_history (function)

`fit_history(turns: list[ConversationTurn], char_limit: int) -> list[ConversationTurn]`

- Returns the longest **contiguous suffix** of `turns` whose total `size` is `≤ char_limit`.
- Whole turns only. The walk stops at the first turn, from the newest, that does not fit.
- `char_limit == 0` returns `[]`. The result is always a suffix of the input, so order is kept.
- Pure, deterministic, never raises for valid input.

## qa_agent (`qa_agent/models.py`)

### ConversationLogContext (new)

| Field | Type | Rules |
|---|---|---|
| `conversation_id` | `str` | From `ConversationContext`. |
| `turn_index` | `int` | `≥ 1`. |
| `history_turns_used` | `int` | `≥ 0`. Turns passed to the model after `fit_history`. |
| `history_turns_dropped` | `int` | `≥ 0`. `len(context.history) - history_turns_used`. |
| `history_char_limit` | `int` | `≥ 0`. The limit in force for this turn. |
| `prompt_version` | `str` | e.g. `"v2"`. |

### AgentRunLogEntry (extended)

| Field | Change |
|---|---|
| `question` | Unchanged. For a conversation turn, this is the **current message** as typed, not a rewritten question. |
| `conversation` | **New**, `ConversationLogContext \| None = None`. Set by `answer_turn` and `None` for `answer_question`. |

Every other field (`dataset_key`, `outcome`, `timestamp`, `failure`) is unchanged.
`QuestionAnsweringResult` is **unchanged**. `steps` holds only the current turn's
retrievals (research.md R2).

### AgentSettings (extended)

| Field | Type | Default | Env |
|---|---|---|---|
| `history_char_limit` | `int`, `ge=0` | `16_000` | `QA_AGENT_HISTORY_CHAR_LIMIT` |

The standalone path ignores it.

## testset_runner (`testset_runner/conversation_models.py`)

### ScriptedTurn

| Field | Type | Rules |
|---|---|---|
| `message` | `str` | `min_length=1`. |
| `expected` | `str \| None` | Same grammar as `Question.expected` (a number, `~` prefix for ±1%). A non-numeric value is always `needs_review`. |
| `expected_outcome` | `Literal["full","partial","none"] \| None` | Compared exactly with the agent's outcome. |
| `source` | `str \| None` | Where the expected value came from (e.g. `dados_gerais/tb_geral.csv`). |
| `scored` | `bool \| None` | `None` means scored iff `expected` or `expected_outcome` is set. `false` forces a context-only turn. `true` without either expectation is a load error. |

### ScriptedConversation

| Field | Type | Rules |
|---|---|---|
| `id` | `str` | `min_length=1`, unique within the file. |
| `category` | `str` | `min_length=1`. See contracts/conversation-testset.md for the category list. |
| `description` | `str` | Optional, default `""`. |
| `turns` | `list[ScriptedTurn]` | `min_length=1`. |

### ConversationTestset

| Field | Type | Rules |
|---|---|---|
| `path` | `str` | As loaded. |
| `content_hash` | `str` | sha256 of the raw file bytes. This is its identity, as for `Testset`. |
| `conversations` | `list[ScriptedConversation]` | Validated, with unique `id`s. |

### TurnResult

| Field | Type | Notes |
|---|---|---|
| `turn_index` | `int` | 1-based. |
| `message` | `str` | |
| `expected` / `expected_outcome` | as in `ScriptedTurn` | Copied for self-contained run files. |
| `actual_answer` | `str` | |
| `agent_outcome` | `Literal["full","partial","none"]` | |
| `dataset_key` | `str` | |
| `steps` | `list[RetrievalStep]` | Current turn only. |
| `history_turns_sent` | `int` | Turns passed in `ConversationContext.history`, before trimming. |
| `history_turns_used` | `int` | `≥ 0`, `≤ history_turns_sent`. `len(fit_history(history, run.history_char_limit))`, i.e. the turns the model actually received. Lets FR-011 / SC-006 be checked from the run file alone. |
| `status` | `Literal["matched","not_matched","needs_review","errored","unscored"]` | See the scoring rules in contracts/conversation-testset.md. |
| `ungrounded_figures` | `list[str]` | From `grounding.ungrounded_figures`. Empty means none flagged. |
| `attempts` | `int` | `≥ 1`. |
| `failed_attempts` | `list[FailureDetail]` | As in `QuestionResult`. |
| `failure` | `FailureDetail \| None` | Set only when `status == "errored"`. |

### ConversationResult

| Field | Type |
|---|---|
| `conversation_id` | `str` (the scripted `id`) |
| `category` | `str` |
| `turns` | `list[TurnResult]` |

### ConversationRunSummary

| Field | Type | Notes |
|---|---|---|
| `total_conversations` | `int` | |
| `total_turns` | `int` | |
| `scored_turns` | `int` | Turns whose status is not `unscored`. |
| `match_rate` | `float` | `matched / scored_turns`, or 0.0 when nothing is scored. |
| `by_status` | `dict[str, int]` | |
| `by_category` | `dict[str, ConversationRunSummary]` | Nested, one level deep (as `RunSummary`). |
| `turns_with_ungrounded_figures` | `int` | SC-003 screen. Each flagged figure gets a recorded verdict in `results.md` (contracts/conversation-testset.md "Resolving flagged figures"). |
| `target_unreachable` | `bool` | Same rule as `RunSummary`: every turn that reached the model errored. |

### ConversationRun

| Field | Type |
|---|---|
| `run_id` | `str` (`%Y%m%dT%H%M%S%fZ`, as `TestRun`) |
| `created_at` | `datetime` |
| `testset` | `ConversationTestset` |
| `target` | `TargetConfiguration` (no credential) |
| `retry_policy` | `RetryPolicy` |
| `history_char_limit` | `int` |
| `prompt_version` | `str` |
| `results` | `list[ConversationResult]` |
| `summary` | `ConversationRunSummary` |

## Relationships and lifecycle

```text
browser chat (id, messages[])
   └─ chat_api._conversation_from ─► (message, ConversationContext{history: [ConversationTurn…]})
                                          │
ScriptedConversation.turns ──runner──────►│  (history = prior scripted msgs + actual answers)
                                          ▼
                           ConversationalAnswerer.answer_turn
                                          │  select_dataset(message)        (every turn)
                                          │  fit_history(history, limit)    (oldest dropped)
                                          │  StepBudget(limit=10)           (fresh per turn)
                                          │  run_sync(message, message_history, instructions=v2)
                                          ▼
                           QuestionAnsweringResult ──► AgentRunLogEntry{conversation=…}
                                          │
                                          └─runner─► TurnResult ─► ConversationResult ─► ConversationRun
```

Nothing about a conversation is held in memory between requests. Each request or scripted
turn rebuilds its `ConversationContext` from scratch.
