"""CLI: `run`/`compare` subcommands (research.md §9).

Every flag has a QA_AGENT_*-prefixed environment-variable fallback, but flags exist
specifically so two different runs in the same shell session never require
re-exporting an environment variable between them (US3).
"""

import argparse
import os
import sys

from testset_runner.comparator import compare_runs
from testset_runner.exceptions import IncompatibleRunsError, RunLoadError, TestsetLoadError
from testset_runner.models import TargetConfiguration
from testset_runner.question_answerer import QaAgentQuestionAnswerer
from testset_runner.runner import run_testset
from testset_runner.store import JsonFileRunStore


def _run(args: argparse.Namespace) -> int:
    model = args.model or os.environ.get("QA_AGENT_MODEL")
    if not model:
        print("Error: --model is required (or set QA_AGENT_MODEL).", file=sys.stderr)
        return 1
    base_url = args.base_url or os.environ.get("QA_AGENT_BASE_URL")
    api_key = args.api_key or os.environ.get("QA_AGENT_API_KEY")

    target = TargetConfiguration(model_name=model, base_url=base_url)
    answerer = QaAgentQuestionAnswerer(target, api_key=api_key)
    store = JsonFileRunStore(args.out_dir)

    try:
        run = run_testset(args.testset, target, answerer=answerer, store=store)
    except TestsetLoadError as exc:
        print(f"Error: could not load testset — {exc}", file=sys.stderr)
        return 1

    print(f"Run {run.run_id}: {run.summary.total_questions} questions")
    if run.summary.target_unreachable:
        print(
            "WARNING: the target model/URL appears unreachable for the whole run — "
            "the match rate below is not meaningful."
        )
    print(f"Match rate: {run.summary.match_rate:.1%}")
    print("By category:")
    for category, cat_summary in sorted(run.summary.by_category.items()):
        print(
            f"  {category}: {cat_summary.match_rate:.1%} "
            f"({cat_summary.total_questions} questions)"
        )
    print(f"Saved run to {args.out_dir.rstrip('/')}/{run.run_id}.json")
    return 0


def _compare(args: argparse.Namespace) -> int:
    store = JsonFileRunStore("data/testset_runs")

    try:
        comparison = compare_runs(args.run_a, args.run_b, store=store)
    except RunLoadError as exc:
        print(f"Error: could not load a run — {exc}", file=sys.stderr)
        return 1
    except IncompatibleRunsError as exc:
        print(f"Error: the two runs are not comparable — {exc}", file=sys.stderr)
        return 1

    print(
        f"Run A: model={comparison.run_a.model_name} base_url={comparison.run_a.base_url}"
    )
    print(
        f"Run B: model={comparison.run_b.model_name} base_url={comparison.run_b.base_url}"
    )
    print()
    for transition, count in sorted(comparison.summary.items()):
        print(f"  {transition}: {count}")
    print()
    for entry in comparison.entries:
        if entry.transition in ("newly_passing", "newly_failing"):
            print(f"  [{entry.transition}] n={entry.n}: {entry.question}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="testset_runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--testset", required=True)
    run_parser.add_argument("--model")
    run_parser.add_argument("--base-url")
    run_parser.add_argument("--api-key")
    run_parser.add_argument("--out-dir", default="data/testset_runs")
    run_parser.set_defaults(func=_run)

    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("run_a")
    compare_parser.add_argument("run_b")
    compare_parser.set_defaults(func=_compare)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
