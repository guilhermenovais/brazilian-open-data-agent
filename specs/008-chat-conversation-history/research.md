# Research: Conversational Context in the Web UI Chat

Phase 0 output for [plan.md](./plan.md). The Technical Context had no open
`NEEDS CLARIFICATION` items. The three spec clarifications (visible text only, a scripted
conversation runner, size-based trimming) fixed the main design forks. The decisions below
settle how each requirement is built.

## R1. Where the history comes from: the browser's payload, no server-side store

**Decision**: On every `POST /api/chat`, rebuild the conversation from the `messages` array
the bundled chat UI already sends (Vercel AI SDK `SubmitMessage`/`RegenerateMessage`, both
`{id, messages[]}`). The server keeps no session state.

**Rationale**:
- The payload already holds exactly what the user sees (005 contracts/chat-api.md step 2,
  which today discards it). FR-010 (edited and regenerated messages in their current form,
  discarded versions excluded) is met by construction. On regenerate, the AI SDK client
  slices its message list to before the regenerated assistant message before sending.
- FR-007/FR-008 (per-chat isolation, a new chat starts empty) also hold by construction:
  each browser chat sends only its own messages, so there is no shared server state that
  could leak between tabs.
- The spec keeps server-side and cross-restart persistence out of scope and trusts
  browser-sent history like the question itself (spec Assumptions, 005 Assumptions).

**Alternatives considered**:
- *Server-side dict keyed by chat `id`*: duplicates state the client already holds. It
  would need eviction, would diverge from the UI on edit or regenerate (breaking FR-010),
  and would be a module-level global (Eng. 4). Rejected.
- *`VercelAIAdapter.messages` / `load_messages`*: converts UI messages to `ModelMessage`s
  directly, but carries every part type (tool, reasoning, file) and ties `qa_agent` to the
  UI format. FR-001 requires visible text only. Rejected in favour of an explicit,
  text-only parse in `chat_api` (R7).

## R2. How the history reaches the model: pydantic-ai `message_history`

**Decision**: Convert each kept `ConversationTurn` into
`ModelRequest(parts=[UserPromptPart(question)])` followed by
`ModelResponse(parts=[TextPart(answer)])` (the response is omitted when the turn has no
reply). Pass the list as `agent.run_sync(message, message_history=…, instructions=…)`.

**Rationale**:
- This is the framework's native multi-turn mechanism. Roles stay correct for the
  provider, and Logfire/OTel traces show the history without extra code (Eng. 9).
- `instructions` are applied per run and are not taken from history in pydantic-ai 2.45, so
  each turn's system prompt reflects that turn's own dataset selection and prompt version.
- Prior turns carry only text. No `ToolCallPart`/`ToolReturnPart` is ever built, which
  satisfies FR-001 and forces re-retrieval (FR-005).
- `_extract_steps(run_result.all_messages())` would also see history messages, but those
  contain no tool parts, so `steps` still holds only the current turn's retrievals. To be
  explicit, extraction switches to `run_result.new_messages()`, which is identical for the
  standalone path because there `all_messages() == new_messages()`.

**Alternatives considered**:
- *Inline transcript in the user prompt* ("Conversa anterior: …\nPergunta atual: …"):
  mixes roles, weakens the model's sense of which text is the current question, and makes
  the model input differ even for turn 1. Rejected.
- *Condense the follow-up into a standalone question first* (an extra LLM call):
  doubles model calls per turn, adds a second place where model judgment can fail, and
  hides the user's real text from the answering run. Worth reconsidering only with
  evidence from the conversation runner (Principle II). Rejected for now.

## R3. History size limit: characters, whole turns, oldest dropped first

**Decision**: `fit_history(turns, char_limit)` walks from the newest turn backwards and
adds `len(question) + len(answer or "")` per turn. It stops at the **first** turn that does
not fit, so kept turns are always a contiguous, most-recent suffix. The current message is
never counted or dropped. `char_limit=0` means no history. Default is
`AgentSettings.history_char_limit = 16_000`.

**Rationale**:
- Characters are deterministic and provider-independent (Principles V/VI). A token
  budget would need a per-model tokenizer, which no current dependency provides for every
  target (OpenAI, OpenRouter, local vLLM).
- Sizing against real data: across recorded testset runs, the median question is 77 chars
  and the median answer 129 chars (p90 214). With listing answers budgeted generously at
  about 800 chars per turn, 16,000 chars holds 20 or more turns (FR-011, SC-006). That is
  roughly 4–5k tokens, on top of a system prompt of about 12k chars (prompt + briefing),
  which stays well inside a 32k-context local model.
- Stopping at the first turn that doesn't fit, instead of skipping it and packing smaller
  older turns, keeps the context coherent. The model never sees turn 3 without turn 4.
- A single turn larger than the whole limit gets dropped along with everything older, and
  the turn is still answered (FR-011: never fail).

**Alternatives considered**: token counting (above); a fixed turn count (the spec
clarification chose size); summarising dropped turns (an extra model call plus
fabrication risk). All rejected.

## R4. Prompt: a new versioned `system_v2.md`, used only on the conversational path

**Decision**: Create `qa_agent/prompts/system_v2.md`: all eight v1 rules unchanged (FR-012),
with rule 2 reworded from "neste mesmo atendimento" to "nesta mesma resposta, durante o
turno atual", plus a "Conversa" section. The new section says:
- earlier messages serve **only** to interpret the current message (FR-002/FR-005)
- if the previous reply asked for clarification, the new message may be the answer to it,
  and should then be combined with the original question (FR-003)
- a message that is complete on its own does not inherit subject, period, filter or metric
  (FR-004)
- when a reference is ambiguous, pick the most reasonable reading and state it (FR-006)
- values from earlier replies must be re-queried, never repeated (FR-005)
- earlier failure or decline messages are not facts (Edge Cases)

`prompt_loader.render(briefing, version="v1")` gains a `version` parameter. `answer_question`
keeps calling it with the default, and `answer_turn` passes `"v2"`. The version is recorded
in the log `conversation` block and in `ConversationRun`.

**Rationale**: Eng. 8 forbids editing `system_v1.md` in place. Keeping v1 on the standalone
path makes the testset runner's model input byte-identical (FR-014, SC-007). v2 is used for
**every** web UI turn, including turn 1, so which prompt applies never depends on a hidden
"has history?" switch. The runner's fresh-chat cases (SC-005) measure turn-1 behavior
under v2 directly.

**Alternatives considered**: using v2 for all paths (breaks SC-007); v1 for turn 1 and v2
afterwards (two behaviors in one chat, harder to reason about). Both rejected.

## R5. qa_agent entry point: `answer_turn` beside `answer_question`

**Decision**: Add
`answer_turn(message, *, context: ConversationContext, selector, selection_logger, run_logger, settings)`.
It runs dataset selection on the current `message` (deterministic and context-free, per spec
Assumptions), applies `fit_history(context.history, settings.history_char_limit)`, and calls
the shared `_answer_with_selection`. That function gains keyword-only `history`,
`prompt_version` and `log_context` parameters, with defaults that reproduce today's
behavior exactly. `answer_question` stays unchanged. Every turn builds a new `StepBudget`,
as today (FR-009). Failures are translated exactly as in `answer_question` and logged with
the conversation block.

**Rationale**: FR-014 and the spec Assumption ("adds a conversational path next to it rather
than replacing it"). A shared private core means the no-fabrication, failure-translation
and outcome-clamp rules cannot drift between the two paths (FR-012).

## R6. Seam: `ConversationalAnswerer` Protocol

**Decision**: In `qa_agent/answerer.py`, add
`class ConversationalAnswerer(Protocol): def answer_turn(self, message: str, context: ConversationContext) -> QuestionAnsweringResult`.
`QaAgentQuestionAnswerer` implements both `answer` and `answer_turn`, and takes a
`history_char_limit` constructor argument that is forwarded into `AgentSettings`.
`web_ui.create_app`/`build_chat_endpoint` and `run_conversations` are typed against
`ConversationalAnswerer`.

**Rationale**: two real consumers (web UI, conversation runner) plus test doubles
(Eng. 2). Keeping the method separate from `answer` means the standalone `QuestionAnswerer`
contract, and every existing double of it, is untouched.

## R7. Parsing UI messages into turns (web_ui)

**Decision**: `chat_api._conversation_from(run_input) -> tuple[str, ConversationContext] | None`:
1. Find the **last** `user` message with non-empty text. That is the current message, and
   anything after it is ignored. If there is none, return `None`, which gives today's empty
   `FinishChunk` response.
2. For the messages before it, in order: each non-empty `user` message opens a new turn;
   the text of each following `assistant` message (joined `TextUIPart.text`, stripped) is
   appended to that turn's `answer`. `system` messages, non-text parts and assistant text
   before any user message are ignored. A user message with no reply becomes a turn with
   `answer=None`, as happens when a request failed with an `ErrorChunk`.
3. `conversation_id = run_input.id` (the chat id the UI uses in its URL);
   `turn_index = len(history) + 1`.

**Rationale**: implements FR-001 (visible text only), FR-010 and FR-013 with pure,
unit-testable code. Failure replies produced by `answer_question` (e.g. "Não foi possível
processar a pergunta…") are normal assistant text and stay in history. v2 tells the model
they are not facts (Edge Cases).

## R8. Usage log extension

**Decision**: `AgentRunLogEntry.conversation: ConversationLogContext | None = None`, with
`conversation_id`, `turn_index`, `history_turns_used`, `history_turns_dropped`,
`history_char_limit` and `prompt_version`. Standalone entries carry `null`.

**Rationale**: FR-013 needs the conversation and position. The trimming numbers and prompt
version cost little and make SC-006 and prompt comparisons analysable from the log alone
(Principle X, FR-011 "recorded with each run"). Nesting keeps the standalone entry shape
flat and backward-compatible: old lines still validate.

## R9. Scripted conversation test set

**Decision**: A new JSON file, `data/testsets/conversations/orcamentos-aeb-csv-conversations.json`,
holds a list of conversations with `id`, `category` and `turns`. Each turn has a `message`,
an optional `expected` (numeric, graded with the existing `NumericMatchStrategy`), an
optional `expected_outcome` (`full`/`partial`/`none`, compared deterministically with the
agent's outcome), an optional `source`, and `scored` (default `true` when either expectation
is set). Only the turn a criterion measures is scored; context turns set `scored: false`, so each
category's match rate reads directly as its criterion. Categories map to the success criteria:

| Category | Covers | Example turns |
|---|---|---|
| `follow-up-year` | SC-001, US1-AS1 | "Quanto foi pago pela AEB em 2015?" → "e em 2016?" |
| `follow-up-metric` | SC-001, US1-AS2 | "… pago … 2015?" → "e quanto foi empenhado?" |
| `follow-up-reference` | SC-001, US1-AS3 | "quais as 3 ações com maior valor pago em 2012?" → "qual dessas teve o menor valor empenhado?" |
| `clarification` | SC-002, US2-AS1 | "Me fale sobre o orçamento." (`scored: false`) → "o valor pago em 2015" (scored) |
| `clarification-insufficient` | US2-AS2 | vague question (`scored: false`) → a reply that is still underspecified (`expected_outcome: none`) |
| `clarification-ignored` | US2-AS3 | vague question → an unrelated complete question |
| `standalone-after-unrelated` | SC-004, US1-AS4 | a question about 2015 → a complete question about another year and subject |
| `fresh-chat-follow-up` | SC-005, US3-AS1 | single turn "e em 2016?" with `expected_outcome: none` |
| `long-conversation` | SC-006 | one 20+ turn conversation; every turn must be non-errored |

Expected values are computed deterministically from the dataset (pandas over
`dados_gerais/tb_geral.csv`, recorded in each turn's `source`), the same way the 004
testsets were built. Model judgment never decides them (Principle VI). There should be at
least 3 conversations per SC-001/SC-002 category, so a 90% threshold means something.

**Rationale**: FR-015 requires the listed coverage. Numeric grading plus outcome checks
make SC-001/002/004/005 mechanical. Text-only expectations follow the existing matcher rule
and fall to `needs_review`, never auto-guessed.

## R10. Conversation runner: `testset_runner run-conversations`

**Decision**: `run_conversations(testset_path, target, *, answerer: ConversationalAnswerer,
store, history_char_limit, matcher=NumericMatchStrategy(), retry_policy=RetryPolicy(), sleep=time.sleep)`.
- Each scripted conversation starts from empty history (SC-005 isolation). For turn *k*,
  history is the scripted messages 1..k-1 paired with the agent's **actual** answers from
  this run, which is exactly what the web UI would have shown and sent.
  `conversation_id = f"{run_id}:{conversation.id}"`.
- Each turn runs under the existing `RetryPolicy`. `runner._ask_with_retry` is generalized
  to take `ask: Callable[[], QuestionAnsweringResult]`, a mechanical refactor with no
  behavior change for `run_testset`. An errored turn does not stop the conversation, and
  its failure answer text goes into history, as in the UI.
- Turn status: `errored` if errored; otherwise the worse of the `expected` grade and the
  `expected_outcome` check (`not_matched` < `needs_review` < `matched`); `unscored` if
  neither applies. Each turn also records `ungrounded_figures` (R11).
- Summary: turn totals, match rate over scored turns, per-category breakdown, count of
  turns with ungrounded figures, and `target_unreachable`, following the same rule as
  `run_testset`.
- Persisted as `ConversationRun` to `data/conversation_runs/<run_id>.json`, with test-set
  hash, target, retry policy, `history_char_limit` and `prompt_version`.

**Rationale**: FR-015 requires replay "through the same conversational path the web UI
uses". Both call `ConversationalAnswerer.answer_turn` with a `ConversationContext`, and
trimming and prompting happen inside `qa_agent`. The only web-specific step (R7 parsing)
is unit-tested on its own. Reusing matcher, retry and the store pattern keeps this small
(VII). A separate subcommand and separate modules leave `run` untouched (FR-014).

**Alternatives considered**: driving the runner through HTTP (`TestClient` + SSE
decoding). That is more faithful to the transport but adds a Starlette dependency to the
evaluation path and SSE parsing for no extra coverage of answering behavior. Rejected. A
comparator for conversation runs is not required by the spec and is deferred (VII).

## R11. Figure-grounding check for SC-003

**Decision**: `grounding.ungrounded_figures(answer, message, steps) -> list[str]`:
extract every numeric substring of the answer with the matcher's (now public) regex and
parse it with `parse_locale_number`. A figure is grounded when its value equals a number
parsed from any of the **current turn's** `steps[].result_summary` or from the current
user message. Everything else is returned. Turns with a non-empty list are counted in the
summary and flagged for review. They are not auto-failed, because a legitimate computed
value (e.g. a difference between two retrieved sums) is a known false positive. Each
flagged figure instead gets a recorded `derived` / `ungrounded` verdict with a reason,
keyed by run id, conversation id and turn index, in `results.md`. SC-003 holds when there
are zero `ungrounded` verdicts (contracts/conversation-testset.md "Resolving flagged figures").

**Rationale**: SC-003 ("0% of answers state a figure not retrieved during that same turn")
needs a mechanical, reproducible screen (Principles I/VI). Because `steps` holds only the
current turn's retrievals (R2), a figure copied from an earlier answer without
re-querying, the exact failure FR-005 forbids, is flagged.

## R12. CLI and configuration

**Decision**:
- `AgentSettings.history_char_limit: int = Field(16_000, ge=0)` (env `QA_AGENT_HISTORY_CHAR_LIMIT`).
- `web_ui.cli --history-char-limit` and
  `testset_runner.cli run-conversations --history-char-limit`, with flag-over-env
  precedence as in 005/006. The web UI prints the active limit at startup, next to the URL.
- `run-conversations` flags: `--testset`, `--model`, `--base-url`, `--api-key`,
  `--max-attempts`, `--history-char-limit` and `--out-dir` (default
  `data/conversation_runs`).

**Rationale**: FR-011 requires the limit to be set "in the run configuration and recorded
with each run". This follows Eng. 7 and the existing CLI conventions.
