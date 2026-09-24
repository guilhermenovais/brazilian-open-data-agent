# Research: CLI Web UI Launcher

All items below were "NEEDS CLARIFICATION" only in the generic sense that the
spec doesn't prescribe an implementation; each is resolved here from reading
the installed `pydantic-ai==2.45.0` source and the existing codebase
(`qa_agent`, `dataset_selector`, `testset_runner`).

## R1: How does pydantic-ai's own "web UI" feature work, and can it be used as-is?

**Decision**: Do not mount `pydantic_ai.ui._web.create_web_app` (a.k.a.
`pydantic-ai web <agent>` / the CLI's `run_web_command`) unmodified. Serve the
same bundled chat UI HTML it uses, but implement the `/api/chat` endpoint
ourselves.

**Rationale**: `create_web_app`/`create_api_app` build exactly one `Agent`
object and accept exactly one static `deps`, `instructions`, and (optionally) a
fixed list of `models` — all fixed at app-construction time and reused for
every request for the life of the process (confirmed by reading
`pydantic_ai/ui/_web/app.py` and `api.py`: `deps`/`instructions`/`model_settings`
are parameters of `create_web_app`, not of the per-request `post_chat`
handler). This project's agent is different: which dataset (and therefore
which `AgentDeps` and which system-prompt briefing) applies is resolved *per
question*, deterministically, by `dataset_selector.StaticDatasetSelector`,
*before* any model call — this is Constitution Principle VI ("Deterministic
Computation Over Model Judgment") applied on purpose: the agent itself never
decides which dataset to use. A single static `deps` for the whole process
would either hard-code one dataset (breaking every other dataset) or require
pushing dataset selection into the model's tool-calling loop (a real
behavioral change, and a Principle VI violation) to work around the static
`deps`. Neither is acceptable, so the generic web-UI app is not reusable as-is
for the chat *logic* — only for the UI shell it serves.

**Alternatives considered**:
- *Use `create_web_app` with dataset selection turned into an agent tool* —
  rejected: changes what "outcome"/"grounded answer" means, contradicts
  FR-009 ("same question-answering behavior... used by the project's other
  entry points") and Principle VI.
- *Mutate the `Starlette` app `create_web_app` returns, swapping its `/api`
  `Mount` for a custom one* — rejected: relies on undocumented internal route
  list structure of a third-party app object; more fragile than writing a
  small, explicit app (Principle VII: no speculative cleverness for its own
  sake).

## R2: How to answer a chat question so the web UI and `testset_runner` stay identical (FR-009, SC-004)

**Decision**: The `/api/chat` handler calls the exact same seam
`testset_runner` already uses — `QaAgentQuestionAnswerer.answer(question)` —
run in a thread pool (Starlette handlers are async; `answer_question` is a
blocking call that may make a real HTTP request to a model provider).

**Rationale**: `testset_runner.question_answerer.QaAgentQuestionAnswerer`
already wraps `qa_agent.capabilities.answer_question` with exactly the pieces
a "give me an answer for this one question, using this target
model/URL/key" caller needs: it builds the `AgentSettings`, the
`StaticDatasetSelector`, and the selection/run loggers once, and exposes a
single `.answer(question) -> QuestionAnsweringResult` method with no
testset-specific behavior in it. Calling it from `web_ui` means the web UI
gets dataset selection, retrieval, outcome classification, the Portuguese
fallback messages for "no dataset"/"processing failed", and outcome-clamping
via `StepBudget`, all for free and byte-for-byte identical to the testset
runner — because it is the same code path, not a re-implementation. This
directly satisfies FR-009 and SC-004 by construction rather than by
convention, and Constitution Principle X ("usage as research data") is
satisfied for free too, since `_finalize` already writes the
`JsonlRunLogger`/`JsonlSelectionLogger` entries on every call.

**Consequence for project structure**: `QuestionAnswerer`/`QaAgentQuestionAnswerer`
currently live under `testset_runner/question_answerer.py`, a leaf package.
With a second, unrelated consumer (`web_ui`), leaving it there would mean
`web_ui` importing from `testset_runner` — backwards layering (a CLI tool
importing from another CLI tool). Per Engineering Principle 2 ("define an
interface before the second implementation... trying a new approach must mean
writing a new class against an existing interface, never editing callers"),
this is exactly the moment to promote the seam: move it to `qa_agent/answerer.py`
(no content changes needed — it already has zero testset-specific logic) and
have both `testset_runner` and `web_ui` import it from there.

**Alternatives considered**:
- *Have `web_ui` build its own `AgentSettings`/`StaticDatasetSelector`/logger
  wiring, duplicating `QaAgentQuestionAnswerer`* — rejected: duplicates
  behavior that must stay identical to satisfy SC-004; any future change
  (e.g., a new logger field) would need to land in two places.
  a real `Agent.run`, and would require re-implementing `answer_question`'s
  exception→fallback-message translation and outcome-clamping to avoid
  drift — the same duplication problem, one layer deeper. Rejected for the
  same reason.

## R3: How to speak the Vercel AI SDK wire protocol the bundled chat UI expects

**Decision**: Use `pydantic_ai.ui.vercel_ai.VercelAIAdapter` only for its
public, non-agent-execution pieces:
- `VercelAIAdapter.from_request(request, agent=<qa_agent instance>, sdk_version=7)`
  to parse the incoming request (handles the SDK's v5/v6/v7 request-shape
  differences) and read the latest user message text from `adapter.run_input`.
- The typed chunk models in `pydantic_ai.ui.vercel_ai.response_types`
  (`StartChunk`, `TextStartChunk`, `TextDeltaChunk`, `TextEndChunk`,
  `FinishChunk`, `ErrorChunk`) to represent the answer.
- `adapter.streaming_response(chunk_stream)` to encode those chunks as the
  correctly-negotiated SSE/JSON response.

None of these require actually running the agent through the adapter
(`run_stream`/`dispatch_request`) — they operate on a plain
`AsyncIterator[BaseChunk]`, which `chat_api.py` builds itself from the
`QuestionAnsweringResult` returned by R2's `answer()` call: one `StartChunk`,
one `TextStartChunk`, one `TextDeltaChunk` carrying the whole answer text (no
token-level streaming — the answer is already fully computed by the time we
have it), one `TextEndChunk`, one `FinishChunk`.

**Rationale**: This is the smallest design that (a) never hand-rolls the wire
protocol's byte format (avoids drift against the bundled UI version pinned by
`CHAT_UI_VERSION`/`sdk_version=7`), (b) never depends on pydantic-ai's private
`pydantic_ai.ui._web` internals, and (c) never asks the adapter to execute an
`Agent.run` with the wrong (static) deps — sidestepping R1's blocker entirely
by only using the adapter as an encoder/decoder, not a runner.

**Alternatives considered**:
- *Hand-write the SSE bytes directly* — rejected: reinvents a versioned
  protocol pydantic-ai already models as typed, public pydantic classes;
  strictly more risk for no benefit.
- *Feed pydantic-ai's internal native agent-stream events into
  `adapter.transform_stream`* — rejected: those event types describe a live
  `Agent.iter()` run in progress; fabricating them to represent an
  already-finished answer is more indirect and more coupled to internals than
  building the public `response_types` chunks directly.

## R4: Serving the chat UI's HTML, and host validation

**Decision**: Fetch the bundled UI HTML once (from the same public CDN URL
pydantic-ai's own `create_web_app` uses by default) at first request and hold
it in memory for the life of the process; serve it from `web_ui/html.py`.
Reimplement the `Host`-header check directly (compare against the configured
`--host` plus IP literals/`localhost`) rather than importing
`pydantic_ai.ui._web._hosts.HostValidationMiddleware`.

**Rationale**: `pydantic_ai.ui._web.app._get_ui_html` implements
filesystem caching (XDG cache dir, atomic writes, per-URL cache files) which
is real engineering effort but solves a problem this feature doesn't have —
this is a single local dev process, not something restarted thousands of
times a day where a persistent on-disk cache pays for itself. An in-memory,
fetch-once cache is a few lines, has no private-API dependency, and is
sufficient for SC-001 (a fresh process reaching a working browser in under 30
seconds — one extra CDN fetch on first request is well within budget). The
DNS-rebinding rationale for host validation (a website the developer has open
must not be able to reach this unauthenticated local server by pointing a
hostname it controls at `127.0.0.1`) is worth keeping — R1 already rules out
depending on `pydantic_ai.ui._web`'s app assembly, and the check itself is a
single header comparison, so reimplementing it is cheaper and more
transparent than importing a private middleware class just for this.

**Alternatives considered**:
- *Import `pydantic_ai.ui._web.app._get_ui_html` / `HostValidationMiddleware`
  directly* — rejected: both are private (underscore-package); importing them
  couples `web_ui` to pydantic-ai internals that can change without a
  deprecation window, for a benefit (disk-persistent HTML cache across
  process restarts) this tool doesn't need, and for a check simple enough to
  own directly.
- *Vendor/self-host the HTML file* — rejected as unnecessary for a first
  version; can be revisited if offline use becomes a requirement.
- *Skip host validation entirely* — rejected: this is a local dev server with
  no authentication that can execute arbitrary configured dataset
  tools/queries; the DNS-rebinding risk pydantic-ai's own implementation
  guards against applies equally here.

## R5: CLI shape and configuration precedence

**Decision**: Mirror `testset_runner/cli.py` exactly: `--model`, `--base-url`,
`--api-key` fall back to `QA_AGENT_MODEL`/`QA_AGENT_BASE_URL`/`QA_AGENT_API_KEY`
(the same env vars the testset runner and `AgentSettings` already use — not a
new prefix, so a developer who has already exported these for the testset
runner gets the web UI "for free", per FR-002/FR-003's flag-over-env
precedence). `--host`/`--port` are new to this command and fall back to
`QA_WEB_HOST`/`QA_WEB_PORT` (default `127.0.0.1`/`8000`), keeping the
existing `AgentSettings` env prefix scoped to agent config only.

**Rationale**: Consistency with the one existing CLI in the codebase; the
project has exactly one prior art to match, and the spec explicitly calls out
that a second, inconsistent configuration surface is a risk to avoid
(User Story 2's "Why this priority"). Missing model resolves to a clear
stderr error and exit code 1 without starting the server (FR-004), identical
to `testset_runner`'s `_run`.

**Alternatives considered**: A single `QA_WEB_*`-only prefix for everything —
rejected, would force re-exporting model/URL/key variables already set for
the testset runner, defeating FR-002's "without permanently exporting
environment variables if they don't want to" for users who already have them
set for the other entry point.

## R6: Port-in-use / bind failures (User Story 3)

**Decision**: Let `uvicorn`'s underlying socket bind raise `OSError` (`errno
EADDRINUSE` on Linux/macOS); catch it in `cli.py` around the `uvicorn.run(...)`
call (or an explicit pre-bind check) and print a clear
`Error: <host>:<port> is already in use` message to stderr with exit code 1,
matching the FR-005/User-Story-3 requirement for "a clear error identifying
the port conflict" rather than an uvicorn traceback.

**Rationale**: No new dependency needed; `OSError.errno == errno.EADDRINUSE`
is the standard, portable way to detect this on the platforms in scope
(Target Platform: Linux/macOS).
