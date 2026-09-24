# Implementation Plan: CLI Web UI Launcher

**Branch**: `005-cli-web-ui` | **Date**: 2026-09-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-cli-web-ui/spec.md`

## Summary

Add a command-line entry point that starts a local web-based chat interface for
the existing question-answering agent, using pydantic-ai's bundled web chat UI
(`pydantic_ai.ui.vercel_ai` / the `@pydantic/ai-chat-ui` frontend it serves) as
the frontend. Model, base URL, API key, host, and port are configurable via
flags with `QA_AGENT_*`/`QA_WEB_*` environment-variable fallbacks, mirroring
`testset_runner`'s CLI. The chat endpoint does not run the agent through
pydantic-ai's generic web-UI request handler (which assumes one static
`deps`/`instructions` pair for the whole process); instead it resolves the
per-question dataset deterministically and calls the project's existing
`answer_question` capability exactly as `testset_runner` does, then encodes
that result into the Vercel AI SDK wire format the bundled UI expects. This
keeps dataset selection outside model judgment (Constitution Principle VI) and
guarantees the web UI and the testset runner produce identical answers for the
same question and configuration (FR-009, SC-004).

## Technical Context

**Language/Version**: Python 3.11+ (repo floor; local `.venv` runs 3.12)

**Primary Dependencies**: `pydantic-ai` (already resolves `pydantic-ai-slim[web]`,
which brings `starlette`, `uvicorn`, `sse-starlette` — no new `pyproject.toml`
dependency needed), `pydantic-settings`, the project's existing `qa_agent` and
`dataset_selector` packages

**Storage**: N/A — conversation state lives only in the browser (Vercel AI
SDK's client-side chat state); the existing JSONL run/selection logs under
`data/logs/` continue to be written per question via the reused `answer_question`
call, unchanged

**Testing**: pytest — `tests/unit/web_ui/` for CLI flag wiring and the chat
chunk encoder (pure functions, no server), `tests/contract/web_ui/` for the
`/api/chat` HTTP contract using Starlette's `TestClient` with a `FunctionModel`
so no real model call is made, following the existing contract-test pattern in
`tests/contract/qa_agent/`

**Target Platform**: Linux/macOS developer workstation (local CLI + local web
server); no container or deployment target in scope

**Project Type**: Single project — extends the existing `src/` package layout
with one new top-level component (`web_ui`) plus a small relocation inside
`qa_agent`/`testset_runner` (see Structure Decision); no separate frontend
project, since the UI is the CDN-hosted HTML pydantic-ai already ships

**Performance Goals**: SC-001 — command to a working chat interface in the
browser in under 30 seconds on a local machine; no throughput/latency target
beyond that (single-operator local tool)

**Constraints**: MUST NOT print or log the configured API key anywhere
(FR-011); MUST default to binding a local-only interface, requiring deliberate
opt-in to broader exposure (spec Assumptions); MUST keep concurrent
browser sessions fully isolated with no server-side session state (FR-012)

**Scale/Scope**: Single running process, one model/endpoint configuration per
process (spec Assumptions), a handful of concurrent browser tabs at most

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|---|---|
| I. Reproducibility | No new empirical/accuracy claim is made by this feature; it reuses the existing, already-reproducible `answer_question` path. PASS |
| II. Evidence Before Implementation | Behavior change is driven by the spec's documented user stories/FRs, not speculation. PASS |
| III. Documentation Is a Deliverable | This plan's artifacts (research/data-model/contracts/quickstart) plus module docstrings written during implementation cover it. PASS |
| IV. Tests Document Behavior | Contract tests for `/api/chat` and unit tests for CLI flag precedence / chunk encoding are planned as behavior specs, following existing test-naming conventions. PASS |
| V. Separate Mechanism from Domain Knowledge | `web_ui` contains no dataset-specific logic; it only wires HTTP ↔ the existing generic `answer_question` capability. PASS |
| VI. Deterministic Computation Over Model Judgment | Dataset selection stays a deterministic, pre-model-loop step (`StaticDatasetSelector`), exactly as today — the web layer explicitly avoids pydantic-ai's generic web-UI flow because that flow would require picking one static deps/dataset for the whole process or pushing selection into the model loop. PASS |
| VII. Code Quality Is Enforced | See research.md decisions R2/R3: reuse of public, typed pydantic-ai chunk models instead of hand-rolled protocol bytes or reliance on private `pydantic_ai.ui._web` internals; a small, justified extraction of the existing `QaAgentQuestionAnswerer` seam out of `testset_runner` (see Structure Decision) rather than a new parallel implementation. PASS |
| VIII. Security and Data Stewardship | API key flows only through `AgentSettings`/`OpenAIProvider` as today; never included in printed URLs, CLI banners, or the request/response chunks sent to the browser. PASS |
| IX. Continuous Integration Gate | New code ships with pytest coverage and passes `pyright src/`; no CI config change needed (`pytest tests/contract tests/unit` and `pyright src/` already cover new paths under `src/`/`tests/`). PASS |
| X. Usage as Research Data | Because the web layer calls the same `answer_question` path, every web-UI question is still recorded by the existing `JsonlRunLogger`/`JsonlSelectionLogger` with no new code required. PASS |

No violations — Complexity Tracking table is not needed.

**Post-Phase-1 re-check**: research.md (R1–R6) and data-model.md were written
against this same table — the design that came out of Phase 0/1 (custom
`/api/chat` reusing `QaAgentQuestionAnswerer`, deterministic dataset selection
kept outside the model loop, no server-side session state, API key never
logged) is what the table above already assesses. No new violations were
introduced by the detailed design; the table stands unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/005-cli-web-ui/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── cli.md
│   └── chat-api.md
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── qa_agent/
│   ├── answerer.py        # MOVED here from testset_runner/question_answerer.py:
│   │                       # QuestionAnswerer protocol + QaAgentQuestionAnswerer.
│   │                       # It has no testset-specific content today; a second
│   │                       # consumer (web_ui) makes it a shared qa_agent seam
│   │                       # rather than something borrowed from a sibling leaf
│   │                       # package (Engineering Principle 2).
│   ├── agent_factory.py    # unchanged
│   ├── capabilities.py     # unchanged
│   └── ...
├── testset_runner/
│   ├── cli.py              # updated import: qa_agent.answerer instead of
│   │                       # testset_runner.question_answerer
│   └── ...                 # question_answerer.py removed
├── web_ui/                 # NEW component
│   ├── __init__.py
│   ├── settings.py          # WebServerSettings: host, port (pydantic-settings,
│   │                       # env prefix QA_WEB_)
│   ├── chat_api.py          # /api/chat Starlette route: parses the Vercel AI
│   │                       # SDK request, extracts the latest user question,
│   │                       # calls QaAgentQuestionAnswerer.answer in a
│   │                       # threadpool, encodes the QuestionAnsweringResult as
│   │                       # a Vercel AI SDK chunk stream (contracts/chat-api.md)
│   ├── html.py              # minimal HTML-serving route for the bundled chat
│   │                       # UI (fetch-once, serve-from-memory; no dependency
│   │                       # on pydantic_ai's private caching internals)
│   ├── app.py                # Starlette app factory wiring html.py + chat_api.py
│   └── cli.py                # argparse CLI: --model/--base-url/--api-key/
│                              # --host/--port, QA_AGENT_*/QA_WEB_* env fallback,
│                              # prints the reachable URL, handles port-in-use
│
tests/
├── unit/
│   └── web_ui/
│       ├── test_cli.py           # flag/env precedence, missing-model error
│       └── test_chat_api_encoding.py  # QuestionAnsweringResult -> chunk stream
└── contract/
    └── web_ui/
        └── test_chat_endpoint.py  # HTTP-level: POST /api/chat with a
                                    # FunctionModel-backed agent, asserts the
                                    # response matches answer_question's output
```

**Structure Decision**: Single project, extending the existing flat `src/`
package layout with one new top-level package (`web_ui`) that depends on
`qa_agent` and `dataset_selector` the same way `testset_runner` already does.
No `frontend/`/`backend/` split: the chat frontend is the CDN-hosted HTML
`pydantic-ai` ships, not a project we build or version here. The only
structural change to existing code is relocating the already-generic
`QuestionAnswerer`/`QaAgentQuestionAnswerer` seam from `testset_runner` into
`qa_agent`, where both consumers can depend on it without a leaf-package cross-import.
