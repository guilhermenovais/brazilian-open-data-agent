# Contract: CLI changes

Flag-over-env precedence follows 005/006: an explicitly passed flag wins, then the env var,
then the default.

## `python -m web_ui.cli`

New flag:

| Flag | Env fallback | Default | Validation |
|---|---|---|---|
| `--history-char-limit` | `QA_AGENT_HISTORY_CHAR_LIMIT` | `16000` | integer ≥ 0, otherwise `Error: --history-char-limit must be an integer >= 0.` on stderr, exit 1 |

The value is passed to `QaAgentQuestionAnswerer(history_char_limit=…)`. The startup output
gains one line after the URL line:

```text
Chat UI available at: http://127.0.0.1:8000
Conversation history limit: 16000 characters
```

All other flags and behavior are unchanged.

## `python -m testset_runner.cli run-conversations` (new subcommand)

| Flag | Env fallback | Default |
|---|---|---|
| `--testset` (required) | — | — |
| `--model` | `QA_AGENT_MODEL` | required |
| `--base-url` | `QA_AGENT_BASE_URL` | none |
| `--api-key` | `QA_AGENT_API_KEY` | none |
| `--max-attempts` | `QA_AGENT_MAX_ATTEMPTS` | `3` |
| `--history-char-limit` | `QA_AGENT_HISTORY_CHAR_LIMIT` | `16000` |
| `--out-dir` | — | `data/conversation_runs` |

Errors (stderr, exit 1): the same messages as `run` for a missing model, a bad
`--max-attempts` and a test set that fails to load (`Error: could not load testset — …`),
plus the `--history-char-limit` message above.

Report (stdout, exit 0):

```text
Run <run_id>: <C> conversations, <T> turns (<S> scored)
[WARNING: the target model/URL appears unreachable for the whole run — the match rate below is not meaningful.]
Match rate (scored turns): 91.7%
By category:
  clarification: 100.0% (3 scored turns)
  follow-up-year: 100.0% (3 scored turns)
  …
Turns with ungrounded figures: 0
Retry policy: max_attempts=3, waits 2.0s x2.0 (cap 60.0s)
History limit: 16000 characters; prompt: v2
Saved run to data/conversation_runs/<run_id>.json
```

## `python -m testset_runner.cli run` / `compare`

Unchanged (FR-014).
