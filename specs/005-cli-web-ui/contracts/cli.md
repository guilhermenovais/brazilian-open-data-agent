# Contract: `web_ui` CLI

Invocation: `python -m web_ui.cli [flags]` (matches how `testset_runner` is
run today — no console-script entry point exists in this repo yet for either
tool).

## Flags

| Flag | Env var fallback | Required | Notes |
|---|---|---|---|
| `--model` | `QA_AGENT_MODEL` | Yes (from one of the two) | FR-002, FR-004 |
| `--base-url` | `QA_AGENT_BASE_URL` | No | FR-002 |
| `--api-key` | `QA_AGENT_API_KEY` | No | FR-002, FR-011 — never echoed anywhere |
| `--host` | `QA_WEB_HOST` | No, default `127.0.0.1` | FR-005 |
| `--port` | `QA_WEB_PORT` | No, default `8000` | FR-005 |

**Precedence**: for every flag/env pair, an explicitly-passed flag wins over
the environment variable (FR-003). This applies independently per setting —
e.g. `--model` from a flag with `QA_AGENT_BASE_URL` from the environment is
valid and combines both.

## Behavior

1. **No model resolvable** (`--model` absent and `QA_AGENT_MODEL` unset):
   print `Error: --model is required (or set QA_AGENT_MODEL).` to stderr,
   exit code `1`, and do not start the server (FR-004). No partial server
   state is created.
2. **Requested port already bound**: print
   `Error: <host>:<port> is already in use.` to stderr, exit code `1`. No
   retry, no automatic port selection (User Story 3, Acceptance Scenario 1).
3. **Successful startup**: bind the server, then print
   `Chat UI available at: http://<host>:<port>` to stdout (FR-006). The
   printed URL reflects whatever `--host`/`--port` (or their env/defaults)
   actually resolved to (User Story 3, Acceptance Scenario 2).
4. The process runs until interrupted (Ctrl+C / SIGINT), matching standard
   `uvicorn.run` behavior; exit code `0` on a clean interrupt.

## Explicitly out of scope for this contract

- Config file support — flags and environment variables only, matching
  `testset_runner`.
- Multiple models/endpoints selectable from the running UI — one
  configuration per process (spec Assumptions).
