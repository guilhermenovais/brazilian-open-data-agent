# Contract: Prompt Version Selection and Run Record

**Covers**: FR-001–FR-004, FR-008–FR-011 · US1 AC3, US4 · research §1–§5, §10

## `qa_agent.prompt_loader`

```python
DEFAULT_PROMPT_VERSION: str = "v2"

def available_versions() -> list[str]: ...
    # Sorted version names ("v1", "v2", ...) from prompts/system_<name>.md.
def check_version(version: str) -> None: ...
    # Raises UnknownPromptVersionError(requested, available) if not available.
def render(briefing: str, version: str = DEFAULT_PROMPT_VERSION) -> str: ...
    # check_version(version), then template.format(briefing=briefing).
def fingerprint(text: str) -> str: ...
    # hashlib.sha256(text.encode("utf-8")).hexdigest()
```

Existing callers of `render(briefing)` now get v2. The one production caller
(`_answer_with_selection`) passes `settings.prompt_version` explicitly.

## `qa_agent.settings.AgentSettings`

`prompt_version: str = DEFAULT_PROMPT_VERSION`, with env `QA_AGENT_PROMPT_VERSION`. A
`field_validator` calls `check_version`, so a bad value makes construction raise
`pydantic.ValidationError`.

## `qa_agent.answerer.QaAgentQuestionAnswerer`

```python
def __init__(self, model_name, base_url=None, *, api_key=None,
             prompt_version: str | None = None, ...) -> None
    # If prompt_version is not None, check_version() is called first. It raises
    # UnknownPromptVersionError before any selector, logger or settings object is built.
    # When None, AgentSettings resolves it (env, then default).
@property
def prompt_version(self) -> str   # the resolved settings.prompt_version
```

`QuestionAnswerer` (the Protocol) is **unchanged**. `prompt_version` is specific to the
concrete class and is read by the CLIs only.

## `qa_agent.capabilities`

- `_answer_with_selection` renders with `render(selection.briefing, settings.prompt_version)`
  and sets `briefing_fingerprint=fingerprint(selection.briefing)` on every result it
  finalizes, including the agent-exception path.
- The dataset-selection failure path leaves `briefing_fingerprint=None`.
- `_clamp_outcome(reported: Outcome, budget) -> Outcome`: `needs_clarification` is never
  downgraded (FR-004).

## `testset_runner.run_testset`

- Signature unchanged. `target.prompt_version` is persisted as given.
- `TestRun.briefing_fingerprints = sorted({r.briefing_fingerprint for r in answers if r.briefing_fingerprint})`,
  where `answers` is the final `QuestionAnsweringResult` of each question.

## `testset_runner.compare_runs`

- Transitions and the incompatible-testset check are **unchanged**.
- Adds `briefing_fingerprints_a`, `briefing_fingerprints_b` and
  `briefing_fingerprints_differ` to `RunComparison`.

## CLIs

### `python -m testset_runner.cli run`

| Flag | Env fallback | Default |
|---|---|---|
| `--prompt-version` | `QA_AGENT_PROMPT_VERSION` | `v2` (via `AgentSettings`) |

- Unknown version: prints `Error: unknown prompt version 'v9' (available: v1, v2).` to
  stderr and exits 1. The testset is not loaded, no question is asked and no run file is
  written (FR-009, US4 AC3).
- On success, the existing summary gains:

  ```text
  Prompt version: v2
  Briefing fingerprint: 3f5a9c0d12ab
  ```

  The fingerprint shows the first 12 hex characters. If there are several, they are
  comma-separated. If there are none, it prints `none`.

### `python -m testset_runner.cli compare A B`

```text
Run A: model=… base_url=… prompt_version=v1
  retry policy: …
  briefing fingerprint: 3f5a9c0d12ab
Run B: model=… base_url=… prompt_version=v2
  retry policy: …
  briefing fingerprint: 3f5a9c0d12ab
Briefing fingerprints differ: no
```

Any value that is `None` prints as `not recorded` (US4 AC4, AC5).

### `python -m web_ui.cli`

- New `--prompt-version` flag, with env fallback `QA_AGENT_PROMPT_VERSION` and default v2.
- Unknown version: the same error line, exit 1, before the port check or the bind.

### `python -m qa_agent.eval_harness`

- Reads `QA_AGENT_PROMPT_VERSION` through `AgentSettings()`.
- The recorded `settings` already includes `prompt_version`.

## Backward compatibility (FR-003, SC-006)

| Stored artifact | New field | Loads as |
|---|---|---|
| `TestRun` JSON (any earlier version) | `target.prompt_version`, `briefing_fingerprints`, `results[].expected_outcome` | `None`, `None`, `None` |
| `qa_agent_runs.jsonl` line | none (`outcome` widened) | unchanged |
| Testset JSON without `expected_outcome` | `expected_outcome` | `None` |

## Test obligations

Tests are named `test_008_us4_<M>_...` and `test_008_us1_<M>_...`.

- **US4-1**:
  - `AgentSettings(model_name="m").prompt_version == "v2"`.
  - The runner CLI without a flag passes `target.prompt_version == "v2"` to a
    monkeypatched `run_testset` (the existing `tests/unit/testset_runner/test_cli.py` seam).
- **US4-2**: `--prompt-version v1` → the stored `target.prompt_version == "v1"`.
- **US4-3**:
  - `v9` → exit 1. stderr names `v9` and lists `v1, v2`. The monkeypatched `run_testset`
    was never called.
  - `QaAgentQuestionAnswerer(..., prompt_version="v9")` raises `UnknownPromptVersionError`.
- **US4-4**: the `pre-006-run.json` fixture loads. `prompt_version` / `briefing_fingerprints`
  are `None`, and `compare` prints "not recorded".
- **US4-5**: comparing two runs with different versions shows both versions. The transitions
  equal those computed without the new fields.
- **US4-6**:
  - Two runs with a fake answerer returning the same briefing text have equal fingerprints.
  - A changed text gives a different fingerprint.
  - `fingerprint` is SHA-256 of the UTF-8 bytes.
- **US1-3**: `_clamp_outcome(reported="needs_clarification", budget with 0 successes) == "needs_clarification"`.
  A scripted-model contract test through `_answer_with_selection` returns
  `needs_clarification` with zero tool calls.
- A scripted `AgentAnswer(outcome="needs_clarification")` validates. A log entry with it
  round-trips through `JsonlRunLogger`.
