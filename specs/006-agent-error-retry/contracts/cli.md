# Contract: `testset_runner` CLI changes

This extends the `004` CLI (`src/testset_runner/cli.py`).

## `run`: new flag

| Flag | Env fallback | Default | Validation |
|------|--------------|---------|------------|
| `--max-attempts N` | `QA_AGENT_MAX_ATTEMPTS` | `3` | An integer ≥ 1. Anything else prints `Error: --max-attempts must be an integer >= 1.` to stderr and exits `1` before any question is asked. |

The CLI builds `RetryPolicy(max_attempts=N)` with the other fields at their defaults, and passes
it to `run_testset`.

## `run`: output additions

These lines are printed after the existing summary lines:

```text
Retry policy: max_attempts=3, waits 2.0s x2.0 (cap 60.0s)
Questions retried: 4
Errored after exhausting retries: 1
Errored by failure type:
  ConnectError: 3
  AuthenticationError: 1
```

- When `target_unreachable` is set, the existing WARNING line is followed by
  `Most common failure: <type> (<count> questions)`. This covers the spec edge case and SC-005.
- The `Errored by failure type` block is printed only when at least one question errored.

## `compare`: output additions

After each `Run A:` / `Run B:` line:

```text
  retry policy: max_attempts=3, waits 2.0s x2.0 (cap 60.0s)
```

or `  retry policy: not recorded` for a pre-feature run (FR-023, FR-024).

## Unchanged

- The exit codes, the `compare` flags, and the `--out-dir` behavior.
- No credential is ever printed.
