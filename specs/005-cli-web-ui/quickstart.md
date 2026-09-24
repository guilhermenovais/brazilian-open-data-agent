# Quickstart: CLI Web UI Launcher

Validates User Stories 1–3 end-to-end. Assumes the project's existing setup
(`pip install -e ".[dev]"`, `data/briefings`/`data/datasets` populated) is
already done, same as for `testset_runner`.

## Prerequisites

- A reachable model/endpoint — for local validation without external calls,
  point `--base-url` at a local OpenAI-compatible server, or use a real
  provider key.

## US1 — Start a chat session with one command

```bash
python -m web_ui.cli --model gpt-4o-mini
```

- **Expected**: within a few seconds, stdout prints
  `Chat UI available at: http://127.0.0.1:8000` (contracts/cli.md).
- Open that URL in a browser. Type a question that matches an existing
  briefing/dataset (see `data/briefings/` for available topics) and submit
  it.
- **Expected**: the answer appears in the conversation pane. Ask a follow-up
  question in the same tab.
- **Expected**: both the first question/answer and the follow-up are visible
  together (FR-008).

## US2 — Configure model, endpoint, and credentials without editing code

```bash
# explicit flags, no environment configuration
python -m web_ui.cli --model gpt-4o-mini --base-url http://localhost:11434/v1 --api-key sk-local
```

- **Expected**: server starts using exactly that target; a question answered
  through it reflects that model/endpoint (compare against
  `python -m testset_runner.cli run --testset <same testset> --model gpt-4o-mini --base-url http://localhost:11434/v1 --api-key sk-local`
  for the same question — SC-004 requires the answers to match).

```bash
# environment fallback
export QA_AGENT_MODEL=gpt-4o-mini
python -m web_ui.cli
```

- **Expected**: starts using the env-provided model with no flags.

```bash
# flag overrides env
QA_AGENT_MODEL=env-model python -m web_ui.cli --model flag-model
```

- **Expected**: the flag value (`flag-model`) is what's actually used (FR-003).

```bash
# no model anywhere
unset QA_AGENT_MODEL
python -m web_ui.cli
```

- **Expected**: `Error: --model is required (or set QA_AGENT_MODEL).` on
  stderr, exit code `1`, no server started (FR-004).

## US3 — Choose where the web UI listens

```bash
python -m web_ui.cli --model gpt-4o-mini --port 8000 &
python -m web_ui.cli --model gpt-4o-mini --port 8000
```

- **Expected**: the second invocation fails fast with
  `Error: 127.0.0.1:8000 is already in use.`, exit code `1`, instead of
  hanging or a raw traceback (Acceptance Scenario 1).

```bash
python -m web_ui.cli --model gpt-4o-mini --host 0.0.0.0 --port 9000
```

- **Expected**: printed URL reflects `0.0.0.0:9000`; the server is reachable
  at that host/port (Acceptance Scenario 2).

## Edge cases to spot-check in the browser

- Submit an empty message (no text): no request should be sent
  (network tab shows nothing hitting `/api/chat`).
- Ask a question with no matching dataset/briefing: the chat shows the same
  "não foi possível determinar..." style message the testset runner produces
  for an unmatched question, not a raw error or a hung request.
- Open two browser tabs against the same running server, ask different
  questions in each: each tab shows only its own question/answer pairs
  (FR-012).
- Run with a deliberately wrong `--api-key`: the failure surfaces as a chat
  message, not a crash, and `--api-key`'s value never appears in the
  terminal output or in `data/logs/*.jsonl` (FR-011).

## Automated coverage

The scenarios above are also covered without a live model or browser by:
- `tests/unit/web_ui/test_cli.py` — flag/env precedence, missing-model error,
  port-in-use error (mirrors `tests/unit/testset_runner/test_cli.py`'s
  pattern of monkeypatching the underlying call and asserting on captured
  arguments).
- `tests/contract/web_ui/test_chat_endpoint.py` — `POST /api/chat` against a
  `FunctionModel`-backed agent (same technique as
  `tests/contract/qa_agent/test_answer_question_dispatch.py`), asserting the
  response chunk sequence and that it matches what
  `QaAgentQuestionAnswerer.answer` returns directly for the same question.
