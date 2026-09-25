# Contract: Conversational answering (`qa_agent`)

Models: [data-model.md](../data-model.md). Rationale: [research.md](../research.md) R2–R6.

## `qa_agent.conversation.fit_history`

```python
def fit_history(turns: list[ConversationTurn], char_limit: int) -> list[ConversationTurn]
```

Guarantees:

1. The result is a suffix of `turns`, in the same order.
2. `sum(t.size for t in result) <= char_limit`.
3. The result is maximal: adding the turn just before it would exceed `char_limit`.
4. Turns are whole. Text is never truncated.
5. `char_limit == 0` or `turns == []` returns `[]`.

## `qa_agent.capabilities.answer_turn`

```python
def answer_turn(
    message: str,
    *,
    context: ConversationContext,
    selector: DatasetSelector,
    selection_logger: SelectionLogger,
    run_logger: RunLogger,
    settings: AgentSettings,
) -> QuestionAnsweringResult
```

Behavior, in order:

1. `select_dataset(message, …)`. On a selection failure: `_NO_DATASET_ANSWER`,
   `outcome="none"`, `errored=True`, `failure` described as in `answer_question`, and a log
   entry **with** its `conversation` block.
2. `kept = fit_history(context.history, settings.history_char_limit)`.
3. `message_history` = for each `kept` turn, `ModelRequest([UserPromptPart(question)])` and,
   if `answer is not None`, `ModelResponse([TextPart(answer)])`. **No other part types.**
4. A fresh `StepBudget(limit=RETRIEVAL_STEP_LIMIT)` and `AgentDeps`, built exactly as for
   `answer_question` (FR-009).
5. `agent.run_sync(message, deps=…, instructions=render(briefing, version="v2"), message_history=…)`.
6. `steps` are extracted from `run_result.new_messages()`, so they are current-turn only.
7. The outcome clamp, failure translation and `QuestionAnsweringResult` shape are identical
   to `answer_question`.
8. Exactly one `AgentRunLogEntry` per call, with `question=message` and
   `conversation=ConversationLogContext(conversation_id, turn_index, history_turns_used=len(kept),
   history_turns_dropped=len(context.history)-len(kept), history_char_limit, prompt_version="v2")`.

Never raises the exceptions `answer_question` doesn't raise (same catch policy).

## `qa_agent.capabilities.answer_question` (unchanged contract)

The signature, behavior and model input are **byte-identical** to before this feature: no
`message_history`, v1 instructions, and a log entry with `conversation=None` (FR-014, SC-007).
The only internal change is that `_answer_with_selection` gains keyword-only parameters
whose defaults reproduce the old call.

## `qa_agent.prompt_loader.render`

```python
def render(briefing: str, version: str = "v1") -> str
```

Loads `prompts/system_{version}.md` and formats `{briefing}`. An unknown version raises
`FileNotFoundError`. That is a programming error, never reached from user input.
`system_v1.md` is not modified.

`system_v2.md` MUST contain every v1 rule (FR-012) plus a "Conversa" section covering:
interpretation-only use of earlier messages (FR-002/FR-005); a reply to a clarification
request (FR-003); no carry-over into a self-contained message (FR-004); stating the chosen
reading for an ambiguous reference (FR-006); re-querying values from earlier replies
(FR-005); and not treating earlier failure or decline messages as facts (Edge Cases).

## `qa_agent.answerer`

```python
class ConversationalAnswerer(Protocol):
    def answer_turn(self, message: str, context: ConversationContext) -> QuestionAnsweringResult: ...

class QaAgentQuestionAnswerer:            # implements QuestionAnswerer AND ConversationalAnswerer
    def __init__(self, model_name, base_url=None, *, api_key=None,
                 history_char_limit: int = 16_000, …existing roots/log paths…) -> None
    def answer(self, question: str) -> QuestionAnsweringResult          # unchanged
    def answer_turn(self, message: str, context: ConversationContext) -> QuestionAnsweringResult
```

`history_char_limit` is exposed read-only (`.history_char_limit`) so callers can record it.
A module constant `CONVERSATION_PROMPT_VERSION = "v2"` is exported so the runner records
the same value `answer_turn` uses.
