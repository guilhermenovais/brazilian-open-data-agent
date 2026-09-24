# Contract: Web chat HTTP interface

Served by the `web_ui` Starlette app (see research.md R1/R3/R4 for why this
is a custom app rather than `pydantic_ai.ui._web.create_web_app` unmodified).

## `GET /` and `GET /{id}`

Serves the bundled pydantic-ai chat UI HTML (research.md R4). No request
body; response is `text/html`. Identical route shape to pydantic-ai's own
`create_web_app` so the bundled UI's client-side routing (one page per
conversation id) works unmodified.

## `POST /api/chat`

Consumes and produces the Vercel AI SDK "UI Message Stream" protocol
(`sdk_version=7`, matching the bundled UI's `CHAT_UI_VERSION`), via
`pydantic_ai.ui.vercel_ai.VercelAIAdapter` for parsing/encoding only — the
adapter never executes an `Agent.run` itself (research.md R3).

**Request**: `Content-Type: application/json` required (a CSRF control the
adapter already enforces — a non-JSON or missing content type is rejected
with `415` before any agent-side work happens). Body is the Vercel AI SDK
chat request shape: a list of prior messages plus the new user message.

**Handling**:

1. Parse via `VercelAIAdapter.from_request(request, agent=<agent>, sdk_version=7)`.
2. Read the **latest user message's text** from the parsed input. Every
   earlier message in the payload (the client's own conversation history) is
   accepted but ignored for answering purposes — see data-model.md's note on
   why the agent stays stateless per question.
3. **Empty/whitespace-only question**: respond with a `FinishChunk` stream
   containing no assistant text (equivalently, short-circuit before step 4)
   rather than invoking `QaAgentQuestionAnswerer` — avoids writing a
   meaningless run-log/selection-log entry for a no-op submission (Edge
   Cases: "the interface should not send a request to the agent for empty
   input" — enforced server-side as a backstop even though the bundled UI is
   expected to already block empty submits client-side).
4. Otherwise, call `QaAgentQuestionAnswerer.answer(question)` (research.md R2)
   inside a thread pool (`starlette.concurrency.run_in_threadpool`), since
   it's a blocking call.
5. Encode the returned `QuestionAnsweringResult.answer` as one assistant
   message: `StartChunk` → `TextStartChunk` → `TextDeltaChunk(delta=answer)`
   → `TextEndChunk` → `FinishChunk(finish_reason="stop")`.
6. Any *unexpected* exception raised outside `QaAgentQuestionAnswerer.answer`
   itself (which already catches and translates its own failures per
   `answer_question`'s contract — see `qa_agent/capabilities.py`) is caught
   at the route boundary and encoded as an `ErrorChunk`, never as an
   unhandled `500` with a stack trace, and never includes the configured API
   key or raw exception internals in `error_text` (FR-010, FR-011).

**Response**: `Response` built by `adapter.streaming_response(chunks)` —
correct `Content-Type`/framing for whichever transport the request
negotiated (SSE for the bundled UI). Not literally token-streamed (the full
answer is known before chunk 5 starts, since `QaAgentQuestionAnswerer.answer`
is a single blocking call, not a generator) — the chat UI still renders it as
one appended assistant message, satisfying FR-007/FR-008.

## `OPTIONS /api/chat`

CORS preflight: answered with an empty response carrying no
`Access-Control-Allow-*` header, so no cross-origin browser page can reach
this endpoint — same reasoning as pydantic-ai's own `create_api_app`
(a local dev server with no auth must not be reachable by an arbitrary
website the developer happens to have open).

## Host validation

Requests with a `Host` header outside `{host}` (as configured/printed by the
CLI) plus IP literals/`localhost` are refused with `421`, mirroring
`pydantic_ai.ui._web`'s `HostValidationMiddleware` rationale: prevents DNS
rebinding from reaching the local agent process. `web_ui` reimplements this
check directly (a single `Host` header comparison) rather than importing the
private middleware class, consistent with research.md R4's stance on private
internals.
