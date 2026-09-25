"""Before/after analysis of two conversation runs for 009 (T029; research.md R8).

Reads only recorded run files in data/conversation_runs/ and the dataset itself, so every
number in results.md traces to a run id and this script (Constitution Principle I).
Run from the repository root:

    .venv/bin/python specs/009-text-value-matching/analyze_runs.py \\
        --before 20260925T095751382002Z --after <run-id>

Prints:
1. Per-category scored-turn match rates before/after, and per-turn status transitions
   joined by `(conversation_id, turn_index)`.
2. For the after run, every `query_rows`/`aggregate_rows` step with an empty result: its
   text conditions, whether each value matches rows of the source on its own (with the
   009 matcher), whether `value_suggestions` came back, and whether the next step of the
   same turn used a suggested value. Then the SC-004 (b) count: scored turns that failed
   after an empty text-filter result whose value does exist in the source.
3. `inspect_schema("dados_gerais/tb_geral.csv")` JSON size after, and before (the same
   result dumped without the 009 fields `distinct_count`, `values`,
   `value_list_threshold`; 5,994 characters expected).
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from data_access.capabilities import inspect_schema
from data_access.dataset import Dataset
from data_access.models import ContainsCondition, EqualsCondition
from data_access.query_engine import PandasQueryEngine
from data_access.text_matching import MatchRules, TextMatchingConfig
from testset_runner.conversation_models import ConversationRun, TurnResult
from testset_runner.store import JsonFileConversationRunStore

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = REPO_ROOT / "data" / "conversation_runs"
DATASETS_ROOT = REPO_ROOT / "data" / "datasets"
SIZE_DATASET = "orcamentos-aeb-csv"
SIZE_SOURCE = "dados_gerais/tb_geral.csv"
DATA_TOOLS = ("query_rows", "aggregate_rows")
FAILED = ("not_matched", "needs_review", "errored")

TurnKey = tuple[str, int]


def load_run(run_id: str) -> ConversationRun:
    path = RUNS_DIR / f"{run_id}.json"
    if not path.exists():
        raise SystemExit(f"Run file not found: {path}")
    return JsonFileConversationRunStore(RUNS_DIR).load(path)


def turns_by_key(run: ConversationRun) -> dict[TurnKey, tuple[str, TurnResult]]:
    return {
        (conversation.conversation_id, turn.turn_index): (conversation.category, turn)
        for conversation in run.results
        for turn in conversation.turns
    }


def print_categories(before: ConversationRun, after: ConversationRun) -> None:
    print("## 1. Scored turns by category (matched / scored)\n")
    print("| Category | Before | After |")
    print("|---|---|---|")
    categories = sorted(set(before.summary.by_category) | set(after.summary.by_category))
    for category in categories:
        cells = []
        for run in (before, after):
            summary = run.summary.by_category.get(category)
            if summary is None:
                cells.append("-")
                continue
            matched = summary.by_status.get("matched", 0)
            cells.append(f"{matched}/{summary.scored_turns} ({summary.match_rate:.0%})")
        print(f"| {category} | {cells[0]} | {cells[1]} |")
    for label, run in (("Before", before), ("After", after)):
        s = run.summary
        print(
            f"\n{label} ({run.run_id}): {s.by_status.get('matched', 0)}/{s.scored_turns} "
            f"scored turns matched ({s.match_rate:.1%}), by status {dict(sorted(s.by_status.items()))}"
        )


def print_transitions(before: ConversationRun, after: ConversationRun) -> None:
    print("\n### Per-turn status transitions (scored turns)\n")
    turns_before = turns_by_key(before)
    turns_after = turns_by_key(after)
    counts: Counter[str] = Counter()
    changed: list[str] = []
    for key in sorted(turns_before.keys() & turns_after.keys()):
        category, turn_a = turns_before[key]
        _, turn_b = turns_after[key]
        if not (turn_a.scored or turn_b.scored):
            continue
        transition = f"{turn_a.status} -> {turn_b.status}"
        counts[transition] += 1
        if turn_a.status != turn_b.status:
            changed.append(f"| {key[0]} | {key[1]} | {category} | {transition} |")
    for transition, count in sorted(counts.items()):
        print(f"- {transition}: {count}")
    print("\n| Conversation | Turn | Category | Transition |")
    print("|---|---|---|---|")
    print("\n".join(changed) if changed else "| (none) | | | |")


def _text_conditions(step_tool: str, arguments: dict) -> list[EqualsCondition | ContainsCondition]:
    if step_tool == "query_rows":
        raw_filters = arguments.get("filters") or []
    else:
        raw_filters = (arguments.get("request") or {}).get("filters") or []
    conditions: list[EqualsCondition | ContainsCondition] = []
    for raw in raw_filters:
        if raw.get("op") == "equals":
            conditions.append(EqualsCondition.model_validate(raw))
        elif raw.get("op") == "contains":
            conditions.append(ContainsCondition.model_validate(raw))
    return conditions


def _is_empty(result: dict) -> bool:
    return result.get("total_match_count") == 0 or result.get("total_group_count") == 0


def print_zero_row_audit(after: ConversationRun) -> None:
    print("\n## 2. Empty data-tool results with text filters (after run)\n")
    engine = PandasQueryEngine(MatchRules.from_config(after.text_matching or TextMatchingConfig()))
    rows: list[str] = []
    failing_turns_with_existing_value: set[TurnKey] = set()
    for conversation in after.results:
        for turn in conversation.turns:
            for i, step in enumerate(turn.steps):
                if step.tool_name not in DATA_TOOLS:
                    continue
                try:
                    result = json.loads(step.result_summary)
                except json.JSONDecodeError:
                    continue
                if not isinstance(result, dict) or not _is_empty(result):
                    continue
                conditions = _text_conditions(step.tool_name, step.arguments)
                if not conditions:
                    continue
                df = Dataset(DATASETS_ROOT / turn.dataset_key).read(step.arguments["identifier"])
                suggestions = result.get("value_suggestions")
                suggested = {
                    c["value"] for s in (suggestions or []) for c in s.get("candidates", [])
                }
                next_step = turn.steps[i + 1] if i + 1 < len(turn.steps) else None
                next_args = json.dumps(next_step.arguments, ensure_ascii=False) if next_step else ""
                used = any(json.dumps(v, ensure_ascii=False) in next_args for v in suggested)
                for condition in conditions:
                    exists = (
                        condition.field in df.columns
                        and not engine.query_rows(df, [condition]).empty
                    )
                    if exists and turn.scored and turn.status in FAILED:
                        failing_turns_with_existing_value.add(
                            (conversation.conversation_id, turn.turn_index)
                        )
                    rows.append(
                        f"| {conversation.conversation_id} | {turn.turn_index} | {step.tool_name} "
                        f"| {condition.field} {condition.op} {condition.value!r} "
                        f"| {'yes' if exists else 'no'} "
                        f"| {'absent' if suggestions is None else len(suggested)} "
                        f"| {'yes' if used else 'no'} | {turn.status} |"
                    )
    print(
        "| Conversation | Turn | Tool | Text condition | Value in source | "
        "Suggested values | Next step used one | Turn status |"
    )
    print("|---|---|---|---|---|---|---|---|")
    print("\n".join(rows) if rows else "| (none) | | | | | | | |")
    print(
        "\nSC-004 (b): scored turns that failed after an empty text-filter result whose "
        f"value exists in the source: {len(failing_turns_with_existing_value)}"
        + (f" {sorted(failing_turns_with_existing_value)}" if failing_turns_with_existing_value else "")
    )


def print_schema_size() -> None:
    print("\n## 3. inspect_schema size\n")
    result = inspect_schema(Dataset(DATASETS_ROOT / SIZE_DATASET), SIZE_SOURCE)
    after = len(result.model_dump_json())
    before = len(
        result.model_dump_json(
            exclude={
                "value_list_threshold": True,
                "fields": {"__all__": {"distinct_count", "values"}},
            }
        )
    )
    print(f"`{SIZE_SOURCE}`: before {before:,} characters, after {after:,} (+{after - before:,})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--before", required=True, help="run id of the pre-009 conversation run")
    parser.add_argument("--after", required=True, help="run id of the 009 conversation run")
    args = parser.parse_args()

    before = load_run(args.before)
    after = load_run(args.after)
    if before.testset.content_hash != after.testset.content_hash:
        raise SystemExit("The two runs used different conversation test set content.")
    print(f"Before: {before.run_id} (text_matching: {before.text_matching})")
    print(f"After:  {after.run_id} (text_matching: {after.text_matching})\n")
    print_categories(before, after)
    print_transitions(before, after)
    print_zero_row_audit(after)
    print_schema_size()


if __name__ == "__main__":
    main()
