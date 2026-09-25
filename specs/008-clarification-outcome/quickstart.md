# Quickstart: Validating Feature 008

**Feature**: `008-clarification-outcome` · Contracts:
- [grading](./contracts/grading.md)
- [prompt version & run record](./contracts/prompt-version-and-run-record.md)
- [prompt v2](./contracts/prompt-v2.md)

## Prerequisites

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
export QA_AGENT_MODEL=gpt-5.4-nano             # the model used in the evidence run
export QA_AGENT_BASE_URL=https://api.openai.com/v1
export QA_AGENT_API_KEY=...                    # never committed (Principle VIII)
```

## 1. Deterministic gate (CI)

```bash
pytest tests/contract tests/unit -v
pyright src/
```

Expected: all tests green, including the new `test_008_*` tests:
- the grading rules
- `contains_amount`
- the clamp exemption
- version selection and errors
- the fingerprint
- backward-compatible loading
- SC-007 regrading on the committed fixtures
- the v1 SHA-256 pin

No model is called.

## 2. Selection errors fail fast (US4 AC3)

```bash
python -m testset_runner.cli run --testset data/testsets/orcamentos-aeb-csv-10.json --prompt-version v9
# → stderr: Error: unknown prompt version 'v9' (available: v1, v2).   exit code 1, no run file written
python -m web_ui.cli --prompt-version v9
# → same error line, exit 1, nothing listening
```

## 3. Acceptance runs (SC-001–SC-005, SC-008)

Do one run for each version on the **edited** full testset. Don't re-run either one
(Clarification 4).

```bash
python -m testset_runner.cli run --testset data/testsets/orcamentos-aeb-csv.json --prompt-version v1
python -m testset_runner.cli run --testset data/testsets/orcamentos-aeb-csv.json   # default → v2
```

Each summary prints `Prompt version:` and the same `Briefing fingerprint:`. Save both run
IDs as `V1` and `V2`.

```bash
python -m testset_runner.cli compare data/testset_runs/$V1.json data/testset_runs/$V2.json
```

The checks below apply to the comparison output and to the two run files:

| Criterion | How to check | Pass when |
|---|---|---|
| SC-001 | `match_status` of n=48, 49, 50 in V2; the n=49 `actual_answer` is a question | all `matched` |
| SC-002 | `match_status` of n=48, 49, 50 in V1 | all `not_matched` |
| SC-003 | the count of V2 results with `agent_outcome == "needs_clarification"` and `n != 49` | 0 |
| SC-004 | the `newly_failing` count printed by `compare` (A = V1, B = V2) | 0 |
| SC-005 | the helper below prints no hits for V2 (review any hit by hand: it may be a plain Portuguese word) | 0 labels |
| SC-008 | V2 `summary.by_status.needs_review` | ≤ 13 (16 − 3) |

Helper for SC-001/002/003/005/008:

```bash
python - "$V1" "$V2" <<'EOF'
import json, re, sys
label = re.compile(r"\b(full|partial|none|needs_clarification)\b|Classifica[çc][ãa]o\s*:", re.I)
for rid in sys.argv[1:]:
    run = json.load(open(f"data/testset_runs/{rid}.json"))
    by_n = {r["n"]: r for r in run["results"]}
    print(rid, run["target"].get("prompt_version"), run["summary"]["by_status"])
    print("  48-50:", [(n, by_n[n]["agent_outcome"], by_n[n]["match_status"]) for n in (48, 49, 50)])
    print("  clarifications besides #49:",
          [r["n"] for r in run["results"] if r["agent_outcome"] == "needs_clarification" and r["n"] != 49])
    print("  label hits:", [r["n"] for r in run["results"] if label.search(r["actual_answer"])])
EOF
```

If any criterion fails, acceptance fails. The fix is a change to `system_v2.md` or the
briefing, followed by a new pair of runs. Never change the grader to make a run pass.

## 4. Backward compatibility on local data (SC-006, SC-007)

`data/testset_runs/` and `data/logs/` are gitignored, so these checks run locally:

```bash
python - <<'EOF'
import glob
from qa_agent.models import AgentRunLogEntry
from testset_runner.matcher import DeterministicMatcher
from testset_runner.store import JsonFileRunStore
store, grader = JsonFileRunStore("data/testset_runs"), DeterministicMatcher()
for path in sorted(glob.glob("data/testset_runs/*.json")):
    run = store.load(path)                                   # SC-006: must not raise
    changed = [r.n for r in run.results
               if r.match_status != "errored" and r.expected_outcome is None
               and grader.grade(r.expected, r.actual_answer) != r.match_status]
    print(path, "prompt_version:", run.target.prompt_version or "not recorded", "regrade diffs:", changed)  # SC-007: []
for path in glob.glob("data/logs/qa_agent_runs.jsonl"):
    for line in open(path):
        AgentRunLogEntry.model_validate_json(line)           # SC-006: must not raise
print("ok")
EOF
```

Expected: every file loads. Runs from before this feature print `not recorded` and
`regrade diffs: []`.

## 5. Record the results

Write `specs/008-clarification-outcome/results.md` with:
- both run IDs
- the model and base URL
- both prompt versions and the briefing fingerprint
- the value of each SC-001–SC-008 criterion, marked pass or fail

This follows Principle I and the Development Workflow rule on accuracy claims.
