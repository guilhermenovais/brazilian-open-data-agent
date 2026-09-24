---

description: "Task list for CLI Web UI Launcher"
---

# Tasks: CLI Web UI Launcher

**Input**: Design documents from `/specs/005-cli-web-ui/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, contracts/chat-api.md, quickstart.md

**Tests**: Included — plan.md's Testing section and quickstart.md's "Automated coverage" explicitly call for `tests/unit/web_ui/` and `tests/contract/web_ui/`.

**Organization**: Tasks are grouped by user story (spec.md P1/P1/P3) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in every task description

## Path Conventions

Single project (plan.md Structure Decision): `src/<package>/`, `tests/unit/<package>/`, `tests/contract/<package>/` at repository root. No `frontend/`/`backend/` split — the chat UI is CDN-hosted HTML fetched at runtime, not a project we build here.

---

## Phase 1: Setup

**Purpose**: Create the new package skeleton

- [X] T001 Create the `web_ui` package: add `src/web_ui/__init__.py` (empty, just makes `web_ui` importable per `pyproject.toml`'s `[tool.setuptools.packages.find] where = ["src"]`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared seams every user story's implementation calls into

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 [P] Relocate the `QuestionAnswerer` protocol and `QaAgentQuestionAnswerer` class from `src/testset_runner/question_answerer.py` to a new `src/qa_agent/answerer.py` (research.md R2, plan.md Structure Decision). While moving, change `QaAgentQuestionAnswerer.__init__`'s signature from `(self, target: TargetConfiguration, *, api_key=None, ...)` to `(self, model_name: str, base_url: str | None = None, *, api_key: str | None = None, ...)`, building `AgentSettings(model_name=model_name, base_url=base_url, api_key=api_key)` directly — this removes the `from testset_runner.models import TargetConfiguration` import so `qa_agent/answerer.py` has no dependency on `testset_runner` (matching research.md R2's "it already has zero testset-specific logic" claim, since a leaf-package `BaseModel` import is itself testset-specific coupling). Update the call site in `src/testset_runner/cli.py` from `QaAgentQuestionAnswerer(target, api_key=api_key)` to `QaAgentQuestionAnswerer(target.model_name, target.base_url, api_key=api_key)`. Update `src/testset_runner/runner.py`'s `from testset_runner.question_answerer import QuestionAnswerer` to `from qa_agent.answerer import QuestionAnswerer`. Delete `src/testset_runner/question_answerer.py`.
- [X] T003 [P] Create `src/web_ui/settings.py` with `WebServerSettings(BaseSettings)` (data-model.md): `model_config = SettingsConfigDict(env_prefix="QA_WEB_")`; field `host: str = "127.0.0.1"`; field `port: int = 8000` constrained so it "MUST be a valid TCP port (1–65535); enforced by a pydantic field constraint" (data-model.md) — use `Field(default=8000, ge=1, le=65535)`.

**Checkpoint**: `qa_agent.answerer` and `web_ui.settings` exist — user story implementation can begin.

---

## Phase 3: User Story 1 - Start a chat session with one command (Priority: P1) 🎯 MVP

**Goal**: A single command starts a local web server serving the bundled pydantic-ai chat UI; submitting a question in the browser returns the agent's real answer; a follow-up question in the same tab shows both turns.

**Independent Test**: Run `python -m web_ui.cli --model <valid model>`, open the printed URL, submit a question, confirm an answer appears; ask a follow-up and confirm both are visible.

### Implementation for User Story 1

- [X] T004 [P] [US1] Create `src/web_ui/html.py` (research.md R4, contracts/chat-api.md `GET /` and `GET /{id}`): on first request, fetch the bundled pydantic-ai chat UI HTML from the same public CDN URL `pydantic_ai.ui._web.create_web_app` uses by default, cache it in a module-level variable for the life of the process, and expose an async Starlette route handler that returns it as `text/html` for both `GET /` and `GET /{id}` (so the bundled UI's per-conversation client-side routing works unmodified).
- [X] T005 [P] [US1] Create `src/web_ui/chat_api.py` (contracts/chat-api.md `POST /api/chat`, `OPTIONS /api/chat`; data-model.md "New non-persisted types"): implement pure, independently-testable chunk-building functions — `encode_answer_chunks(result: QuestionAnsweringResult) -> list[BaseChunk]` returning `[StartChunk(), TextStartChunk(id=...), TextDeltaChunk(id=..., delta=result.answer), TextEndChunk(id=...), FinishChunk(finish_reason="stop")]` (same `id` across the three text chunks), `encode_empty_chunks() -> list[BaseChunk]` returning just `[FinishChunk(finish_reason="stop")]`, and `encode_error_chunks(message: str) -> list[BaseChunk]` returning `[ErrorChunk(error_text=message)]` (never include the configured API key or raw exception internals in `message` — FR-011). Implement the `POST /api/chat` async handler: parse via `VercelAIAdapter.from_request(request, agent=<qa_agent instance>, sdk_version=7)`, read the latest user message text from `adapter.run_input`; if empty/whitespace, stream `encode_empty_chunks()` without calling the answerer (Edge Cases: no request for empty input); otherwise call `QaAgentQuestionAnswerer.answer(question)` via `starlette.concurrency.run_in_threadpool` and stream `encode_answer_chunks(result)`; catch any exception raised outside the answerer call itself and stream `encode_error_chunks(...)` instead of an unhandled `500` (FR-010); return via `adapter.streaming_response(chunks)`. Implement the `OPTIONS /api/chat` handler returning an empty response with no `Access-Control-Allow-*` header (contracts/chat-api.md CORS section).
- [X] T006 [US1] Create `src/web_ui/app.py` (depends on T004, T005): a `create_app(answerer: QuestionAnswerer, host: str) -> Starlette` factory wiring `GET /` and `GET /{id}` (`html.py`) and `POST /api/chat` + `OPTIONS /api/chat` (`chat_api.py`, with the `answerer` passed through for the handler to call). Add Host-header validation middleware (contracts/chat-api.md "Host validation", research.md R4): reject any request whose `Host` header is not `host` (the configured bind host), an IP literal, or `localhost`/`localhost:<port>` with HTTP `421`, before the request reaches either route — a single header comparison, not an import of `pydantic_ai.ui._web`'s private `HostValidationMiddleware`.
- [X] T007 [US1] Create `src/web_ui/cli.py` (depends on T002, T003, T006; contracts/cli.md items 1, 3, 4): a minimal `main()` that parses `--model` (required — if absent, print `Error: --model is required (or set QA_AGENT_MODEL).` to stderr and exit `1` without starting a server), builds `QaAgentQuestionAnswerer(model)` and a default `WebServerSettings()`, calls `create_app(answerer, host=settings.host)`, prints `Chat UI available at: http://<host>:<port>` to stdout, then runs `uvicorn.run(app, host=settings.host, port=settings.port)`. (Env fallback for `--model`, `--base-url`/`--api-key` flags, and `--host`/`--port` flags are added in US2/US3 below — this task only needs `--model` to make the single-command path work end-to-end.)
- [X] T008 [P] [US1] Create `tests/unit/web_ui/test_chat_api_encoding.py`: unit tests (no server) for `encode_answer_chunks`, `encode_empty_chunks`, `encode_error_chunks` from `web_ui/chat_api.py` — assert the exact chunk type sequence and field values (`TextDeltaChunk.delta == result.answer`, `FinishChunk.finish_reason == "stop"`, matching `id`s across `TextStartChunk`/`TextDeltaChunk`/`TextEndChunk`, `ErrorChunk.error_text` never containing a passed-in secret) (plan.md Testing section).
- [X] T009 [P] [US1] Create `tests/contract/web_ui/test_chat_endpoint.py`: HTTP-level test using Starlette's `TestClient` against `create_app(...)` built with a `FunctionModel`-backed `QaAgentQuestionAnswerer` (same technique as `tests/contract/qa_agent/test_answer_question_dispatch.py`) — `POST /api/chat` with a question matching a fixture briefing/dataset and assert the response's decoded chunk sequence carries the same `answer` text that calling `QaAgentQuestionAnswerer.answer(question)` directly returns (SC-004); also assert an empty-message request produces no answerer call and a malformed/non-JSON request is rejected before reaching the answerer (quickstart.md "Automated coverage").

**Checkpoint**: User Story 1 is fully functional and independently testable — `python -m web_ui.cli --model <model>` serves a working chat UI.

---

## Phase 4: User Story 2 - Configure model, endpoint, and credentials without editing code (Priority: P1)

**Goal**: `--base-url`/`--api-key` flags, environment-variable fallback for all three agent settings, flag-over-env precedence per setting, and a clear failure when no model is resolvable from either source.

**Independent Test**: Launch with explicit `--model`/`--base-url`/`--api-key` flags and confirm that target is used; launch with only env vars set and confirm the same; set both and confirm the flag wins; unset everything and confirm a clear `stderr` error with no server started.

### Implementation for User Story 2

- [X] T010 [US2] Extend `src/web_ui/cli.py` (depends on T007; contracts/cli.md flags table, FR-002/FR-003/FR-004): add `--base-url` and `--api-key` flags. Resolve `model = args.model or os.environ.get("QA_AGENT_MODEL")`, `base_url = args.base_url or os.environ.get("QA_AGENT_BASE_URL")`, `api_key = args.api_key or os.environ.get("QA_AGENT_API_KEY")` — mirroring `testset_runner/cli.py`'s `_run` exactly, so an explicitly-passed flag always wins over the environment variable, independently per setting (FR-003). Keep the existing `Error: --model is required (or set QA_AGENT_MODEL).` / exit `1` / no-server-start behavior for the case where `model` resolves to nothing (FR-004).
- [X] T011 [P] [US2] Create `tests/unit/web_ui/test_cli.py` (mirrors `tests/unit/testset_runner/test_cli.py`'s pattern of monkeypatching the underlying call and asserting on captured arguments): test that explicit `--model`/`--base-url`/`--api-key` flags are used when no env vars are set; test that env vars (`QA_AGENT_MODEL`/`QA_AGENT_BASE_URL`/`QA_AGENT_API_KEY`) are used when flags are omitted; test that a flag overrides an env var set for the same setting (e.g. `QA_AGENT_MODEL=env-model` + `--model flag-model` → `flag-model` wins); test that omitting `--model` with `QA_AGENT_MODEL` unset returns exit code `1` and does not attempt to start a server.

**Checkpoint**: User Stories 1 AND 2 both work independently — model/base-url/api-key are fully configurable via flag or environment, with correct precedence.

---

## Phase 5: User Story 3 - Choose where the web UI listens (Priority: P3)

**Goal**: `--host`/`--port` flags (with `QA_WEB_*` env fallback and the existing `WebServerSettings` defaults), and a clear error instead of a crash/hang when the requested port is already bound.

**Independent Test**: Launch with an explicit `--port` and confirm the server binds there instead of the default; launch a second instance on the same port and confirm a clear error rather than a silent failure or traceback.

### Implementation for User Story 3

- [X] T012 [US3] Extend `src/web_ui/cli.py` (depends on T010; contracts/cli.md `--host`/`--port` rows): add `--host` and `--port` flags. Build `WebServerSettings(host=args.host, port=args.port)` when passed, falling back to `WebServerSettings()`'s own `QA_WEB_HOST`/`QA_WEB_PORT`-env-then-default resolution otherwise (`pydantic-settings` already applies env-var fallback for unset fields — pass only the flags that were explicitly provided so the settings object's own env/default logic still governs the rest, satisfying FR-003's flag-over-env precedence for these two fields as well). Replace T007's hardcoded `WebServerSettings()` call with this. Ensure the printed `Chat UI available at: http://<host>:<port>` reflects whatever `host`/`port` actually resolved to (contracts/cli.md item 3).
- [X] T013 [US3] Extend `src/web_ui/cli.py` (depends on T012; research.md R6, contracts/cli.md item 2): catch the `OSError` (`errno.EADDRINUSE`) raised when `uvicorn.run(...)`'s underlying socket bind fails because the port is already in use, and instead print `Error: <host>:<port> is already in use.` to stderr and exit `1` — no retry, no automatic port selection, no raw traceback (User Story 3 Acceptance Scenario 1).
- [X] T014 [P] [US3] Extend `tests/unit/web_ui/test_cli.py` (depends on T011; quickstart.md US3 scenarios): test that an explicit `--host`/`--port` pair is reflected in the printed URL / passed through to the app factory instead of the defaults; test that `QA_WEB_HOST`/`QA_WEB_PORT` env vars are used when the flags are omitted; test that a simulated `OSError(errno.EADDRINUSE, ...)` from the bind step is caught and produces the `... is already in use.` message with exit code `1`.

**Checkpoint**: All three user stories are independently functional — the full CLI contract (contracts/cli.md) is implemented.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finish the Constitution Check's remaining items (III: documentation, IX: CI gate) and validate the feature as a whole

- [X] T015 [P] Add a short module docstring to each new `src/web_ui/*.py` file (`__init__.py` excluded) explaining its mechanism, following the style already used in `src/testset_runner/question_answerer.py`/`cli.py` (Constitution Principle III).
- [X] T016 Run `pyright src/` and fix any type errors surfaced by the `qa_agent/answerer.py` relocation (T002) or the new `web_ui` package, so the existing CI gate (`pyright src/`, Constitution Principle IX) continues to pass with no config changes.
- [X] T017 Run `pytest tests/contract tests/unit` and fix any failures, confirming the relocated `testset_runner` tests (which import `question_answerer` indirectly through `cli.py`/`runner.py`) still pass alongside the new `tests/unit/web_ui/` and `tests/contract/web_ui/` suites.
- [ ] T018 Manually execute quickstart.md's US1–US3 scenarios end-to-end against a reachable model/endpoint, including the edge cases it lists: submitting an empty message (no `/api/chat` request sent), asking a question with no matching dataset/briefing (shows the same Portuguese fallback message the testset runner produces, not a raw error), opening two browser tabs and confirming isolated conversation histories (FR-012), and running with a deliberately wrong `--api-key` and confirming the key never appears in terminal output or `data/logs/*.jsonl` (FR-011). **Partially done in this session** with real (non-mocked) processes and sockets, without a real model/browser (none available in this sandbox — `QA_AGENT_MODEL=test` was used, which fails at the model-call step): confirmed `GET /` serves the real CDN HTML (200), `POST /api/chat` with a whitespace-only message returns just a `finish` chunk with no answerer call, a question matching `data/briefings/orcamentos-aeb-csv.md` runs real dataset selection and reaches the model-call failure path, returning the same `"Não foi possível processar a pergunta no momento."` fallback text `qa_agent.capabilities` produces elsewhere (not a raw error), a bad `Host` header is rejected with `421`, `OPTIONS /api/chat` carries no CORS header, and a second process on the same `--port` prints `Error: <host>:<port> is already in use.` and exits `1` (this last check caught and fixed a real bug — see completion report). **Still needs the user**: a real model/endpoint + browser to confirm the two-tabs session-isolation and wrong-`--api-key`-non-leak scenarios specifically.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup (T001) completion — BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational (Phase 2) completion.
- **User Story 2 (Phase 4)**: Depends on Foundational (Phase 2) **and** User Story 1's `cli.py` (T007) — it extends the same file.
- **User Story 3 (Phase 5)**: Depends on Foundational (Phase 2) **and** User Story 2's `cli.py` (T010) — it extends the same file.
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

Note: unlike the fully-parallel template default, US2 and US3 here are **sequential extensions of the same `cli.py` file** built in US1, not independent files — each still has its own independently-testable behavior and test file additions (contracts/cli.md is one contract covering all three stories' flags).

### Within Each Phase

- Foundational: T002 and T003 touch disjoint files and have no dependency on each other — parallelizable.
- User Story 1: T004 (`html.py`) and T005 (`chat_api.py`) are disjoint files — parallelizable; T006 (`app.py`) needs both; T007 (`cli.py`) needs T006 (and Foundational's T002/T003); T008/T009 (tests) only need T005/T006 respectively and can run in parallel with each other and with T007.
- User Story 2: T010 is a single sequential edit to `cli.py`; T011 (tests) can be written in parallel once T010's shape is known, or test-first before T010 if practicing TDD.
- User Story 3: T012 then T013, both sequential edits to `cli.py`; T014 (tests) in parallel with either once the CLI shape is settled.

### Parallel Opportunities

- T002 and T003 (Foundational)
- T004 and T005 (User Story 1 implementation)
- T008 and T009 (User Story 1 tests), and either with T007
- T015 (Polish docstrings) alongside T016/T017 once all stories are implemented

---

## Parallel Example: User Story 1

```bash
# Launch the two independent US1 implementation files together:
Task: "Create src/web_ui/html.py — GET / and GET /{id} chat UI HTML serving"
Task: "Create src/web_ui/chat_api.py — POST/OPTIONS /api/chat + pure chunk encoders"

# Once both land, launch the two US1 test files together:
Task: "Create tests/unit/web_ui/test_chat_api_encoding.py"
Task: "Create tests/contract/web_ui/test_chat_endpoint.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001).
2. Complete Phase 2: Foundational (T002–T003) — CRITICAL, blocks all stories.
3. Complete Phase 3: User Story 1 (T004–T009).
4. **STOP and VALIDATE**: `python -m web_ui.cli --model <model>`, open the URL, ask a question, ask a follow-up — matches spec.md's US1 Independent Test.
5. This is already a usable MVP: a working chat command with the model fixed at launch time.

### Incremental Delivery

1. Setup + Foundational → package and shared seams ready.
2. Add User Story 1 → validate independently → usable single-model chat command (MVP!).
3. Add User Story 2 → validate independently → full model/endpoint/credential configurability.
4. Add User Story 3 → validate independently → host/port control and clear port-conflict errors.
5. Polish (T015–T018) → documentation, type-check, full test suite, manual quickstart pass.

---

## Notes

- [P] tasks = different files, no dependencies.
- [Story] label maps task to specific user story for traceability.
- User Story 2 and 3 extend the same `cli.py` built in User Story 1 rather than adding new files — this is a deliberate deviation from "always disjoint files per story" because the CLI contract (contracts/cli.md) is one file for all three stories' flags; each story's slice is still independently described, implemented as a distinct edit, and independently tested.
- Verify new tests fail (or are absent) before their corresponding implementation task, if practicing TDD; none of these are marked "write first" as tests were not explicitly requested to precede implementation in spec.md, but plan.md's Testing section and quickstart.md's "Automated coverage" section do require the listed test files to exist by the end of each story's phase.
- Commit after each task or logical group.
- Stop at any checkpoint to validate a story independently.
