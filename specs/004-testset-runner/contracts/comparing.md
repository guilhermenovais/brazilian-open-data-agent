# Contract: Comparing Two Runs

```python
def compare_runs(
    run_a_path: str | Path,
    run_b_path: str | Path,
    *,
    store: RunStore,
) -> RunComparison: ...
```

The one public entry point of `testset_runner` for User Story 2. A CLI (`cli.py compare`) is
the only caller in this feature.

## Input

- `run_a_path`, `run_b_path: str | Path` — paths to two previously saved `TestRun` files
  (`RunStore.save`'s own output paths — FR-009's "persisted... so a run can be revisited").
- `store: RunStore` — injected, same abstraction `run_testset` uses to write runs, used here to
  read them back.

## Output

`RunComparison` (data-model.md): both runs' `TargetConfiguration`s (FR-010 AS2), and one
`ComparisonEntry` per question — always the full question count, not just the changed subset
(research.md §8, SC-003).

## Raises

| Exception               | When |
|--------------------------|------|
| `RunLoadError`            | Either path doesn't exist or doesn't parse as a valid saved `TestRun`. |
| `IncompatibleRunsError`    | `run_a.testset.content_hash != run_b.testset.content_hash` — the two runs were not made from the same testset content, even if `testset.path` matches (FR-011, Edge Cases). Raised before any `ComparisonEntry` is built; `compare_runs` never returns a partial or best-effort diff in this case. |

## Behavioral requirements (traceability)

| Scenario / Requirement | Behavior |
|-------------------------|----------|
| US2 AS1 (changed questions surfaced) | Every question whose `match_status` differs between `run_a` and `run_b` appears in `entries` with `transition` in `{"newly_passing", "newly_failing"}` (or `"still_failing"` for a failing-to-differently-failing move — data-model.md's `ComparisonEntry`). |
| US2 AS2 (target configs shown) | `RunComparison.run_a`/`run_b` state each run's `model_name`/`base_url` directly — a person never needs to re-open either saved `TestRun` file to see what produced a difference. |
| US2 AS3 (mismatched testsets rejected) | See `IncompatibleRunsError` above — no diff is ever produced across two different testsets. |
| SC-003 (completeness without manual re-checking) | `len(entries) == len(run_a.results) == len(run_b.results)`; `summary`'s transition counts sum to that same length, so totals are self-verifying. |
