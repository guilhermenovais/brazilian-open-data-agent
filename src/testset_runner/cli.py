"""CLI: `run`/`compare`/`run-conversations` subcommands (research.md §9).

Every flag has a QA_AGENT_*-prefixed environment-variable fallback, but flags exist
specifically so two different runs in the same shell session never require
re-exporting an environment variable between them (US3).

`run` flags: `--testset`, `--model` (QA_AGENT_MODEL), `--base-url` (QA_AGENT_BASE_URL),
`--api-key` (QA_AGENT_API_KEY), `--max-attempts` (QA_AGENT_MAX_ATTEMPTS, default 3 — the
attempts per question, 1 disables retries; 006 contracts/cli.md), `--out-dir`.

`run-conversations` (008 contracts/cli.md) takes the same flags plus
`--history-char-limit` (QA_AGENT_HISTORY_CHAR_LIMIT, default 16000). One value configures
both the answerer and the run record, so the recorded `history_turns_used` is what the
model actually received.
"""

import argparse
import os
import sys

from qa_agent.answerer import QaAgentQuestionAnswerer
from testset_runner.comparator import compare_runs
from testset_runner.conversation_runner import run_conversations
from testset_runner.exceptions import IncompatibleRunsError, RunLoadError, TestsetLoadError
from testset_runner.models import RetryPolicy, TargetConfiguration
from testset_runner.runner import run_testset
from testset_runner.store import JsonFileConversationRunStore, JsonFileRunStore


def _run(args: argparse.Namespace) -> int:
    model = args.model or os.environ.get("QA_AGENT_MODEL")
    if not model:
        print("Error: --model is required (or set QA_AGENT_MODEL).", file=sys.stderr)
        return 1
    base_url = args.base_url or os.environ.get("QA_AGENT_BASE_URL")
    api_key = args.api_key or os.environ.get("QA_AGENT_API_KEY")
    max_attempts = _parse_max_attempts(
        args.max_attempts or os.environ.get("QA_AGENT_MAX_ATTEMPTS") or _DEFAULT_MAX_ATTEMPTS
    )
    if max_attempts is None:
        print("Error: --max-attempts must be an integer >= 1.", file=sys.stderr)
        return 1
    retry_policy = RetryPolicy(max_attempts=max_attempts)

    target = TargetConfiguration(model_name=model, base_url=base_url)
    answerer = QaAgentQuestionAnswerer(target.model_name, target.base_url, api_key=api_key)
    store = JsonFileRunStore(args.out_dir)

    try:
        run = run_testset(
            args.testset, target, answerer=answerer, store=store, retry_policy=retry_policy
        )
    except TestsetLoadError as exc:
        print(f"Error: could not load testset — {exc}", file=sys.stderr)
        return 1

    failure_counts = _by_count(run.summary.errored_by_failure_type or {})
    print(f"Run {run.run_id}: {run.summary.total_questions} questions")
    if run.summary.target_unreachable:
        print(
            "WARNING: the target model/URL appears unreachable for the whole run — "
            "the match rate below is not meaningful."
        )
        for failure_type, count in _most_common(failure_counts):
            print(f"Most common failure: {failure_type} ({count} questions)")
    print(f"Match rate: {run.summary.match_rate:.1%}")
    print("By category:")
    for category, cat_summary in sorted(run.summary.by_category.items()):
        print(
            f"  {category}: {cat_summary.match_rate:.1%} "
            f"({cat_summary.total_questions} questions)"
        )
    print(f"Retry policy: {_describe_policy(run.retry_policy)}")
    print(f"Questions retried: {_or_not_recorded(run.summary.retried_questions)}")
    print(
        "Errored after exhausting retries: "
        f"{_or_not_recorded(run.summary.errored_after_retries)}"
    )
    if failure_counts:
        print("Errored by failure type:")
        for failure_type, count in failure_counts:
            print(f"  {failure_type}: {count}")
    print(f"Saved run to {args.out_dir.rstrip('/')}/{run.run_id}.json")
    return 0


def _run_conversations(args: argparse.Namespace) -> int:
    model = args.model or os.environ.get("QA_AGENT_MODEL")
    if not model:
        print("Error: --model is required (or set QA_AGENT_MODEL).", file=sys.stderr)
        return 1
    base_url = args.base_url or os.environ.get("QA_AGENT_BASE_URL")
    api_key = args.api_key or os.environ.get("QA_AGENT_API_KEY")
    max_attempts = _parse_max_attempts(
        args.max_attempts or os.environ.get("QA_AGENT_MAX_ATTEMPTS") or _DEFAULT_MAX_ATTEMPTS
    )
    if max_attempts is None:
        print("Error: --max-attempts must be an integer >= 1.", file=sys.stderr)
        return 1
    history_char_limit = _parse_history_char_limit(
        args.history_char_limit
        or os.environ.get("QA_AGENT_HISTORY_CHAR_LIMIT")
        or _DEFAULT_HISTORY_CHAR_LIMIT
    )
    if history_char_limit is None:
        print("Error: --history-char-limit must be an integer >= 0.", file=sys.stderr)
        return 1
    retry_policy = RetryPolicy(max_attempts=max_attempts)

    target = TargetConfiguration(model_name=model, base_url=base_url)
    answerer = QaAgentQuestionAnswerer(
        target.model_name,
        target.base_url,
        api_key=api_key,
        history_char_limit=history_char_limit,
    )
    store = JsonFileConversationRunStore(args.out_dir)

    try:
        run = run_conversations(
            args.testset,
            target,
            answerer=answerer,
            store=store,
            history_char_limit=answerer.history_char_limit,
            retry_policy=retry_policy,
        )
    except TestsetLoadError as exc:
        print(f"Error: could not load testset — {exc}", file=sys.stderr)
        return 1

    summary = run.summary
    print(
        f"Run {run.run_id}: {summary.total_conversations} conversations, "
        f"{summary.total_turns} turns ({summary.scored_turns} scored)"
    )
    if summary.target_unreachable:
        print(
            "WARNING: the target model/URL appears unreachable for the whole run — "
            "the match rate below is not meaningful."
        )
    print(f"Match rate (scored turns): {summary.match_rate:.1%}")
    print("By category:")
    for category, cat_summary in sorted(summary.by_category.items()):
        print(
            f"  {category}: {cat_summary.match_rate:.1%} "
            f"({cat_summary.scored_turns} scored turns)"
        )
    print(f"Turns with ungrounded figures: {summary.turns_with_ungrounded_figures}")
    print(f"Retry policy: {_describe_policy(run.retry_policy)}")
    print(f"History limit: {run.history_char_limit} characters; prompt: {run.prompt_version}")
    print(f"Saved run to {args.out_dir.rstrip('/')}/{run.run_id}.json")
    return 0


_DEFAULT_MAX_ATTEMPTS = "3"
_DEFAULT_HISTORY_CHAR_LIMIT = "16000"


def _parse_max_attempts(raw: str) -> int | None:
    """The value as an int ≥ 1, or `None` when it is anything else."""
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value >= 1 else None


def _parse_history_char_limit(raw: str) -> int | None:
    """The value as an int ≥ 0, or `None` when it is anything else."""
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value >= 0 else None


def _describe_policy(policy: RetryPolicy | None) -> str:
    if policy is None:
        return "not recorded"
    return (
        f"max_attempts={policy.max_attempts}, waits {policy.initial_wait_seconds}s "
        f"x{policy.backoff_multiplier} (cap {policy.max_wait_seconds}s)"
    )


def _or_not_recorded(value: object | None) -> str:
    return "not recorded" if value is None else str(value)


def _by_count(counts: dict[str, int]) -> list[tuple[str, int]]:
    """Count descending, then type name — the order every failure-type listing uses."""
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def _most_common(ordered: list[tuple[str, int]]) -> list[tuple[str, int]]:
    return [item for item in ordered if item[1] == ordered[0][1]] if ordered else []


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
    print(f"  retry policy: {_describe_policy(comparison.retry_policy_a)}")
    print(
        f"Run B: model={comparison.run_b.model_name} base_url={comparison.run_b.base_url}"
    )
    print(f"  retry policy: {_describe_policy(comparison.retry_policy_b)}")
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
    run_parser.add_argument("--max-attempts")
    run_parser.add_argument("--out-dir", default="data/testset_runs")
    run_parser.set_defaults(func=_run)

    conversations_parser = subparsers.add_parser("run-conversations")
    conversations_parser.add_argument("--testset", required=True)
    conversations_parser.add_argument("--model")
    conversations_parser.add_argument("--base-url")
    conversations_parser.add_argument("--api-key")
    conversations_parser.add_argument("--max-attempts")
    conversations_parser.add_argument("--history-char-limit")
    conversations_parser.add_argument("--out-dir", default="data/conversation_runs")
    conversations_parser.set_defaults(func=_run_conversations)

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
