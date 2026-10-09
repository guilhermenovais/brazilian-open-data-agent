# Contract delta: `POST /api/chat` (supersedes step 2 of 005 contracts/chat-api.md)

Everything in [005's contract](../../005-cli-web-ui/contracts/chat-api.md) still holds:
`GET /`, `GET /{id}`, `OPTIONS`, host validation, 415 on non-JSON, the empty-input
short-circuit, the chunk encoding and the generic error message. The only change is how
the request is turned into an answer.

## Handling (replaces 005 steps 2 and 4)

2. **Build the conversation** from the parsed `run_input` (`SubmitMessage` or
   `RegenerateMessage`, both `{id, messages}`):
   - **Current message**: the text (joined `TextUIPart`s, stripped) of the **last** `user`
     message with non-empty text. Messages after it are ignored.
   - **History**: messages before the current one, in order. Each non-empty `user` message
     opens a `ConversationTurn`. The text of the `assistant` messages that follow it,
     joined with `"\n\n"` and stripped, becomes that turn's `answer`, or `None` if there is
     none. `system` messages, non-text parts (tool, reasoning, file, source…), and assistant
     text before the first user message are dropped (FR-001).
   - `conversation_id = run_input.id`; `turn_index = len(history) + 1`.
4. If a current message exists, call
   `ConversationalAnswerer.answer_turn(message, ConversationContext(...))` in the thread pool.
   Trimming to the history limit happens inside `answer_turn`, not here.

## Guarantees

| Requirement | How it holds |
|---|---|
| FR-001 | Only `TextUIPart` text of user/assistant messages reaches `ConversationTurn`. |
| FR-007 / US3-AS2 | No server-side state. Each request's context comes only from its own payload. |
| FR-008 | A new chat's first request has one user message, so `history == []`. |
| FR-010 | The payload is the UI's current view. Regenerate requests are already sliced by the client. |
| FR-013 | `conversation_id` and `turn_index` are passed on to the run log via `answer_turn`. |
| 005 FR-011 | Unexpected exceptions still become the fixed `ErrorChunk` text. |

## Example

Request (second turn):

```json
{"id": "chat-1", "trigger": "submit-message", "messages": [
  {"id": "m1", "role": "user",      "parts": [{"type": "text", "text": "Quanto foi pago pela AEB em 2015?"}]},
  {"id": "m2", "role": "assistant", "parts": [{"type": "text", "text": "Em 2015, o valor pago foi de R$ …"}]},
  {"id": "m3", "role": "user",      "parts": [{"type": "text", "text": "e em 2016?"}]}
]}
```

Resulting call: `answer_turn("e em 2016?", ConversationContext(conversation_id="chat-1",
turn_index=2, history=[ConversationTurn(question="Quanto foi pago pela AEB em 2015?",
answer="Em 2015, o valor pago foi de R$ …")]))`.
