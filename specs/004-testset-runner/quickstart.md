# Quickstart: Validating the Testset Runner

This is a runnable validation guide, not implementation code — it proves the feature works
end-to-end once built. See `data-model.md` for exact model shapes and `contracts/` for
behavior. Two tracks, same split as `003-qa-agent-workflow`: a **deterministic track** (no API
key, no network — proves the wiring, matching, persistence, and comparison logic) and a
**live-model track** (needs a real model configured — proves the actual bundled sample testset
runs end-to-end against a real answer).

## Prerequisites

- Python 3.11+, project virtualenv with `pydantic-ai`, `pydantic`, `pydantic-settings`,
  `pandas`, `pytest` installed.
- The bundled `data/testsets/orcamentos-aeb-csv.json`, `data/briefings/orcamentos-aeb-csv.md`,
  and `data/datasets/orcamentos-aeb-csv/` (used by the live-model track).
- For the live-model track only: a real model to point at, e.g.
  `--model openai:gpt-4o-mini` with `OPENAI_API_KEY` set, or a self-hosted OpenAI-compatible
  endpoint via `--model <model-id> --base-url http://localhost:8000/v1`.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Deterministic track (CI-gated, no network)

### Scenario 1 — A full run produces one report covering every question (US1 AS1)

```python
from testset_runner.runner import run_testset
from testset_runner.models import TargetConfiguration
from testset_runner.store import JsonFileRunStore

class FakeAnswerer:
    """Returns the testset's own `expected` value verbatim for numeric questions,
    something unrelated for one question, and an errored result for another —
    enough to exercise matched/not_matched/needs_review/errored in one run."""
    def __init__(self):
        self._n = 0
    def answer(self, question: str):
        self._n += 1
        ...  # scripted per the test's own fixture testset

run = run_testset(
    "data/testsets/orcamentos-aeb-csv.json",
    TargetConfiguration(model_name="fake"),
    answerer=FakeAnswerer(),
    store=JsonFileRunStore("data/testset_runs"),
)
assert len(run.results) == 50
assert run.summary.total_questions == 50
```

**Expected outcome**: `run.results` has exactly 50 entries, one per row of the bundled testset,
in file order; a `TestRun` JSON file exists under `data/testset_runs/`.

### Scenario 2 — Numeric matching normalizes formatting, respects the `~` tolerance marker (US1 AS3)

```python
from testset_runner.matcher import DeterministicMatcher

matcher = DeterministicMatcher()
assert matcher.grade("8351", "O valor pago foi de R$ 8.351,00.") == "matched"
assert matcher.grade("8351", "O valor pago foi de R$ 9.000,00.") == "not_matched"
assert matcher.grade("~3675300.51", "O total aproximado foi de R$ 3.675.300,50.") == "matched"
```

### Scenario 3 — Non-numeric expected values are always routed to human review (US1 AS4)

```python
assert matcher.grade(
    "Data not available (no such action/category in the dataset)",
    "Não há dados de merenda escolar para a AEB em 2005.",
) == "needs_review"
assert matcher.grade(
    "Agência Espacial Brasileira / Apoio Administrativo / 238959",
    "A unidade é a Agência Espacial Brasileira, o programa é Apoio Administrativo, valor R$ 238.959,00.",
) == "needs_review"
```

**Expected outcome**: a composite or descriptive `expected` value is never auto-guessed
`"matched"`/`"not_matched"` even when a human would judge it correct or incorrect at a glance
(research.md §5).

### Scenario 4 — A single question's failure doesn't abort the run (US1 AS5, FR-004)

```python
# FakeAnswerer scripted so question n=7 raises inside qa_agent and comes back
# errored=True, outcome="none", answer=<fixed fallback text>
run = run_testset("data/testsets/orcamentos-aeb-csv.json", TargetConfiguration(model_name="fake"),
                   answerer=FakeAnswererWithOneFailure(fail_n=7), store=JsonFileRunStore("data/testset_runs"))
assert len(run.results) == 50
assert next(r for r in run.results if r.n == 7).match_status == "errored"
assert all(r.match_status != "errored" for r in run.results if r.n != 7)
```

### Scenario 5 — A testset with a missing required field fails fast, before any question runs (FR-013)

```python
import pytest
from testset_runner.exceptions import TestsetLoadError
from testset_runner.runner import run_testset

with pytest.raises(TestsetLoadError):
    run_testset("tests/fixtures/testset_runner/missing-expected-field.json",
                TargetConfiguration(model_name="fake"), answerer=FakeAnswerer(),
                store=JsonFileRunStore("data/testset_runs"))
```

### Scenario 6 — Comparing two runs surfaces every changed question, and totals are self-verifying (US2 AS1, SC-003)

```python
from testset_runner.comparator import compare_runs

comparison = compare_runs(run_a_path, run_b_path, store=JsonFileRunStore("data/testset_runs"))
assert len(comparison.entries) == 50
assert sum(comparison.summary.values()) == 50
```

### Scenario 7 — Comparing runs from different testset content is rejected, not silently diffed (US2 AS3)

```python
import pytest
from testset_runner.exceptions import IncompatibleRunsError

with pytest.raises(IncompatibleRunsError):
    compare_runs(run_from_original_file_path, run_from_edited_file_path,
                 store=JsonFileRunStore("data/testset_runs"))
```

## Live-model track (manual / opt-in, not part of the default CI gate)

Requires a real model (hosted, or a self-hosted OpenAI-compatible endpoint).

```bash
# A hosted provider:
python -m testset_runner.cli run \
  --testset data/testsets/orcamentos-aeb-csv.json \
  --model openai:gpt-4o-mini
# OPENAI_API_KEY must already be set in the environment.

# A self-hosted / alternate endpoint, no source change (US3):
python -m testset_runner.cli run \
  --testset data/testsets/orcamentos-aeb-csv.json \
  --model gpt-4o-mini \
  --base-url http://localhost:8000/v1 \
  --api-key not-needed-locally

# Compare the two runs just produced:
python -m testset_runner.cli compare data/testset_runs/<run_id_1>.json data/testset_runs/<run_id_2>.json
```

**Expected outcome**: each `run` invocation prints a one-screen summary — overall match rate,
per-category breakdown, and the saved run file's path (SC-005) — and the `compare` invocation
prints which questions newly passed, newly failed, or are still failing between the two models,
without either run needing to be re-run or manually re-read (SC-003).

## Running the deterministic suite

```bash
pytest tests/contract/testset_runner tests/unit/testset_runner -v
pytest tests/contract/qa_agent tests/unit/qa_agent -v   # unaffected + the new steps/errored coverage
pyright src/
```

**Done when**: all contract tests (one per Acceptance Scenario above) pass with no network
access, unit tests for `TestsetLoader`, `DeterministicMatcher`, `RunStore`, and
`compare_runs`'s transition logic pass in isolation, the extended `qa_agent` contract tests
(new `steps`/`errored` fields) still pass, and `pyright` reports zero errors. The live-model
track is a documented follow-on, not required for this command's own "done," same as `003`'s
own evaluation harness.
