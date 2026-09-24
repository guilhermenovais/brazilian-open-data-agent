# Data Model: CLI Web UI Launcher

This feature introduces one new typed settings object and reuses existing
entities unchanged (`AgentSettings`, `QuestionAnsweringResult`, `AgentAnswer`,
`AgentRunLogEntry`). It does not introduce a persisted "Chat Session" entity —
see the note at the end.

## WebServerSettings (new — `web_ui/settings.py`)

Typed configuration for the network side of the launch command, `pydantic-settings`
`BaseSettings` (Engineering Principle 7), analogous to `qa_agent.settings.AgentSettings`
but scoped to the web server rather than the agent.

| Field | Type | Default | Source |
|---|---|---|---|
| `host` | `str` | `"127.0.0.1"` | `--host` flag, else `QA_WEB_HOST` env var, else default |
| `port` | `int` | `8000` | `--port` flag, else `QA_WEB_PORT` env var, else default |

**Validation rules**: `port` MUST be a valid TCP port (`1–65535`); enforced by
a pydantic field constraint, not by manual argparse validation, so it applies
uniformly whether the value came from the CLI flag or the environment
variable.

**Relationship**: Constructed once per CLI invocation, alongside the existing
`AgentSettings` (model name/base URL/API key/instrument). Together, one
`AgentSettings` + one `WebServerSettings` is the full "Launch Configuration"
the spec's Key Entities section describes — split into two typed objects
because they govern two different things (which model answers questions, vs.
where the HTTP server listens) and because `AgentSettings` already exists and
is reused unchanged.

## Reused entities (no changes)

- **`qa_agent.settings.AgentSettings`** — `model_name`, `base_url`, `api_key`,
  `instrument`. Constructed by `web_ui/cli.py` exactly as `testset_runner/cli.py`
  already does, via `TargetConfiguration` + `QaAgentQuestionAnswerer` (see
  research.md R2).
- **`qa_agent.models.QuestionAnsweringResult`** — `answer`, `dataset_key`,
  `outcome`, `steps`, `errored`. This is what `chat_api.py` receives from
  `QaAgentQuestionAnswerer.answer(question)` and translates into the chat
  UI's wire format (`answer` → the assistant message text; `outcome`/`errored`
  are not currently surfaced in the chat UI, matching the fact that the
  bundled chat UI is a plain text chat and the spec does not ask for an
  outcome badge — only that a failure "display a clear, user-facing message",
  which `answer` already contains verbatim, e.g. the Portuguese
  "não foi possível..." fallbacks).
- **`qa_agent.models.AgentRunLogEntry`** / **`dataset_selector.models.DatasetSelectionLogEntry`** —
  written automatically by the reused `QaAgentQuestionAnswerer.answer` call;
  `web_ui` does not construct these itself.

## New non-persisted types (`web_ui/chat_api.py`)

These exist only to shape the one HTTP response per chat turn; none are
stored, logged, or reused across requests.

- **Chat chunk sequence** — built directly from
  `pydantic_ai.ui.vercel_ai.response_types`, one instance each per turn:
  `StartChunk` → `TextStartChunk` → `TextDeltaChunk(delta=result.answer)` →
  `TextEndChunk` → `FinishChunk`. See contracts/chat-api.md for the exact
  sequence and field values.

## Note: "Chat Session" is a client-side concept, not a server entity

The spec's Key Entities section describes a **Chat Session** as "a single
browser-side conversation... holding the ordered sequence of questions and
answers for the lifetime of that session." Per research.md R3, the Vercel AI
SDK client (the bundled chat UI) already keeps this state itself and resends
the full message list with every request; the server only ever looks at the
latest user message to answer the current turn (see contracts/chat-api.md).
Consequently:

- There is no server-side session store, session ID, or session table to
  model — FR-012's "each session isolated" holds structurally, because
  nothing is shared between requests in the first place.
- The agent does not use prior turns as conversational context when answering
  a follow-up question — each question is answered independently via
  `QaAgentQuestionAnswerer.answer(question)`, identical to how
  `testset_runner` treats every question in a testset independently. This is
  required for SC-004 ("every answer... matches what they would receive...
  through the testset runner") to hold for *every* question in a session, not
  just the first one.
- If conversational memory (the agent seeing prior turns) is wanted later,
  that is a distinct, separately-evaluated feature — out of scope here per
  the spec's own Assumptions ("Conversation history is kept only in memory
  for the life of the running session/process").
