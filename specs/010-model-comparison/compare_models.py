"""Side-by-side comparison of testset runs made against different models (010).

Reads only recorded run files (by default data/testset_runs/; the copies this comparison
used are in evidence/runs/), so every number in results.md traces to a run id and this
script (Constitution Principle I). Run from the repository root:

    .venv/bin/python specs/010-model-comparison/compare_models.py \\
        --runs-dir specs/010-model-comparison/evidence/runs/round2 \\
        qwen3-8b=20261009T... phi-4-mini=20261009T... ...

Prints, as markdown (with `--answers`, prints instead every model's full answer to every
question, with its grade, outcome, tool calls and failure):
1. One row per model: the runner's official match rate and status counts, the provisional
   text check (below), the combined score, per-category rates, errors by failure type,
   mean tool steps per question and retried questions.
2. A question × model matrix (✓ matched, ~ text check passed, ✗ not matched / needs
   review, E errored) to show which questions every model fails.

Text check: the runner grades a question whose `expected` is not a number as
`needs_review` (matcher.py), so the 13 text-valued questions (Q32–34, Q38–47) score 0 for
every model. This script grades only those results, and never changes the run file:
- `expected` is split into parts on " / " and on a trailing "(number)";
- a numeric part must pass the runner's own `NumericMatchStrategy`;
- a text part must appear in the answer after case, accents and punctuation are
  normalized. "X - Y" may match as X, Y or both, and "Agência Espacial Brasileira" may
  match as "AEB";
- the agent's outcome must be `full` or `partial`, so a refusal that merely names the
  agency doesn't pass.
It is a substring check, so a correct paraphrase fails (notably Q47, a definition).
"""

import argparse
import re
import unicodedata
from collections import Counter
from pathlib import Path

from testset_runner.matcher import NumericMatchStrategy
from testset_runner.models import QuestionResult, TestRun
from testset_runner.store import JsonFileRunStore

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = REPO_ROOT / "data" / "testset_runs"
CATEGORIES = ("single-lookup", "calculation", "multiple-files", "edge-cases")
ALIASES = {"agencia espacial brasileira": ("aeb",)}
_TRAILING_NUMBER = re.compile(r"^(.*?)\s*\(([\d.,]+)\)\s*$")
_NUMERIC = NumericMatchStrategy()


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " " + " ".join(re.sub(r"[^\w]+", " ", without_accents).split()) + " "


def expected_parts(expected: str) -> list[str]:
    parts: list[str] = []
    for part in expected.split(" / "):
        trailing = _TRAILING_NUMBER.match(part)
        parts.extend(trailing.groups() if trailing else (part,))
    return [p.strip() for p in parts if p.strip()]


def text_part_found(part: str, normalized_answer: str) -> bool:
    names = {normalize(part)}
    if " - " in part:
        names.update(normalize(side) for side in part.split(" - ") if len(side) >= 4)
    aliases = {f" {alias} " for name in names for alias in ALIASES.get(name.strip(), ())}
    return any(candidate in normalized_answer for candidate in names | aliases)


def text_check(result: QuestionResult) -> bool:
    if result.agent_outcome not in ("full", "partial"):
        return False
    normalized_answer = normalize(result.actual_answer)
    for part in expected_parts(result.expected):
        if re.fullmatch(r"[\d.,]+", part):
            if _NUMERIC.evaluate(part, result.actual_answer) != "matched":
                return False
        elif not text_part_found(part, normalized_answer):
            return False
    return True


def load_run(run_id: str, runs_dir: Path = RUNS_DIR) -> TestRun:
    path = runs_dir / f"{run_id}.json"
    if not path.exists():
        raise SystemExit(f"Run file not found: {path}")
    return JsonFileRunStore(runs_dir).load(path)


def cell(result: QuestionResult) -> str:
    if result.match_status == "matched":
        return "✓"
    if result.match_status == "errored":
        return "E"
    if result.match_status == "needs_review" and text_check(result):
        return "~"
    return "✗"


def pct(numerator: int, denominator: int) -> str:
    return f"{100 * numerator / denominator:.0f}%" if denominator else "–"


def print_summary(runs: dict[str, TestRun]) -> None:
    header = [
        "Model",
        "Official",
        "matched / not / review / err",
        "Text check",
        "Combined",
        *CATEGORIES,
        "Errors by type",
        "Steps/q",
        "Retried",
    ]
    print("| " + " | ".join(header) + " |")
    print("|" + "---|" * len(header))
    for label, run in runs.items():
        results = run.results
        total = len(results)
        status = Counter(r.match_status for r in results)
        review = [r for r in results if r.match_status == "needs_review"]
        text_passed = sum(text_check(r) for r in review)
        per_category = []
        for category in CATEGORIES:
            in_category = [r for r in results if r.category == category]
            passed = sum(
                r.match_status == "matched"
                or (r.match_status == "needs_review" and text_check(r))
                for r in in_category
            )
            per_category.append(f"{passed}/{len(in_category)}")
        errors = run.summary.errored_by_failure_type or {}
        error_text = ", ".join(f"{k} {v}" for k, v in sorted(errors.items())) or "–"
        mean_steps = sum(len(r.steps) for r in results) / total
        combined = status["matched"] + text_passed
        row = [
            f"**{label}**",
            f"{status['matched']}/{total} ({pct(status['matched'], total)})",
            " / ".join(
                str(status[s]) for s in ("matched", "not_matched", "needs_review", "errored")
            ),
            f"{text_passed}/{len(review)}",
            f"**{combined}/{total} ({pct(combined, total)})**",
            *per_category,
            error_text,
            f"{mean_steps:.1f}",
            str(run.summary.retried_questions if run.summary.retried_questions is not None else "–"),
        ]
        print("| " + " | ".join(row) + " |")


def print_matrix(runs: dict[str, TestRun]) -> None:
    by_n = {label: {r.n: r for r in run.results} for label, run in runs.items()}
    first = next(iter(runs.values()))
    print("| Q | Category | " + " | ".join(runs) + " | Passed |")
    print("|" + "---|" * (len(runs) + 3))
    for result in first.results:
        cells = [cell(by_n[label][result.n]) for label in runs]
        passed = sum(c in ("✓", "~") for c in cells)
        print(f"| {result.n} | {result.category} | " + " | ".join(cells) + f" | {passed} |")


GRADE_NAMES = {"✓": "matched", "~": "text check passed", "✗": "not matched", "E": "errored"}


def one_line(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def print_answers(runs: dict[str, TestRun]) -> None:
    by_n = {label: {r.n: r for r in run.results} for label, run in runs.items()}
    first = next(iter(runs.values()))
    for question in first.results:
        print(f"### Q{question.n} ({question.category})\n")
        print(f"**Question**: {question.question}\n")
        print(f"**Expected**: {question.expected}\n")
        print("| Model | Grade | Outcome | Tool calls | Answer / failure |")
        print("|---|---|---|---|---|")
        for label in runs:
            result = by_n[label][question.n]
            grade = cell(result)
            tools = ", ".join(step.tool_name for step in result.steps) or "–"
            text = result.actual_answer
            if result.failure is not None:
                text = f"{result.failure.type}: {result.failure.message}"
            print(
                f"| {label} | {grade} {GRADE_NAMES[grade]} | {result.agent_outcome} | "
                f"{len(result.steps)}: {tools} | {one_line(text)} |"
            )
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare testset runs across models.")
    parser.add_argument("runs", nargs="+", metavar="LABEL=RUN_ID")
    parser.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    parser.add_argument("--answers", action="store_true", help="print every full answer")
    args = parser.parse_args()

    runs: dict[str, TestRun] = {}
    for spec in args.runs:
        label, _, run_id = spec.partition("=")
        if not run_id:
            raise SystemExit(f"Expected LABEL=RUN_ID, got {spec!r}")
        runs[label] = load_run(run_id, args.runs_dir)

    hashes = {run.testset.content_hash for run in runs.values()}
    if len(hashes) > 1:
        raise SystemExit("The runs were made from different testset content.")
    if args.answers:
        print_answers(runs)
        return

    print("## Runs\n")
    print("| Model | Run id | model_name | prompt |")
    print("|---|---|---|---|")
    for label, run in runs.items():
        print(
            f"| {label} | `{run.run_id}` | `{run.target.model_name}` | "
            f"{run.target.prompt_version or '–'} |"
        )
    print("\n## Summary\n")
    print_summary(runs)
    print("\n## Per question\n")
    print_matrix(runs)


if __name__ == "__main__":
    main()
