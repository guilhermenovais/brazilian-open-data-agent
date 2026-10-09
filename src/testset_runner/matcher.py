"""MatchStrategy/DeterministicMatcher: deterministic auto-grading of numeric answers
(research.md §5, Constitution Principle VI), and of the agent's reported outcome when the
testset record states one (008 contracts/grading.md).

Any `expected` value that does not itself parse as a number is always `needs_review`
— never auto-guessed, regardless of how the agent's free-text answer reads — unless the
record's `expected_outcome` lets the answer be graded on its outcome instead.
"""

import re
from typing import Literal, Protocol

from data_access.numeric import parse_locale_number
from qa_agent.models import Outcome

# Public so `grounding.py` finds figures in an answer with exactly the same rule.
NUMERIC_SUBSTRING = re.compile(r"-?\d[\d.,]*\d|-?\d")
_APPROXIMATE_RELATIVE_TOLERANCE = 0.01

_AMOUNT_PATTERNS = (
    re.compile(r"R\$\s*-?\d"),
    re.compile(r"\d[.,]\d"),
    re.compile(r"\d\s*%"),
)
_NO_AMOUNT_OUTCOMES: frozenset[Outcome] = frozenset({"none", "needs_clarification"})


def contains_amount(text: str) -> bool:
    """Whether `text` states an amount, judged only from the text's shape (008 research §6).

    True if any of these appears:
    - `R$` followed by a digit (`R$ 42`, `R$42.750,00`, `R$ -5`) — a currency value;
    - a digit, `.` or `,`, then a digit (`1.234`, `12,5`, `206.805.295`) — a formatted
      number with thousands or decimal separators;
    - a digit followed by `%` (`36%`, `12,5 %`) — a percentage.

    Deliberately allowed: years (`2005`, `2008 a 2012`), list markers (`1.`, `2)`), names
    with numbers (`Amazônia-1`, `CBERS-3`), and `2005, 2006` (a space after the comma).

    Known imprecision: `2005,2006` without a space is flagged as an amount, and a small
    count written as a plain integer ("31 ações") is not caught. The check never looks at
    the dataset, so it can't tell whether a number came from it.
    """
    return any(pattern.search(text) for pattern in _AMOUNT_PATTERNS)


class MatchStrategy(Protocol):
    def evaluate(
        self, expected: str, actual_answer: str
    ) -> Literal["matched", "not_matched", "needs_review"]: ...


class NumericMatchStrategy:
    def evaluate(
        self, expected: str, actual_answer: str
    ) -> Literal["matched", "not_matched", "needs_review"]:
        tolerant = expected.startswith("~")
        bare_expected = expected[1:].strip() if tolerant else expected.strip()
        expected_value = parse_locale_number(bare_expected)
        if expected_value is None:
            return "needs_review"

        for match in NUMERIC_SUBSTRING.finditer(actual_answer):
            candidate = parse_locale_number(match.group())
            if candidate is None:
                continue
            if tolerant:
                tolerance = _APPROXIMATE_RELATIVE_TOLERANCE * max(abs(expected_value), 1.0)
                if abs(candidate - expected_value) <= tolerance:
                    return "matched"
            elif candidate == expected_value:
                return "matched"
        return "not_matched"


class DeterministicMatcher:
    def __init__(self, strategy: MatchStrategy | None = None) -> None:
        self._strategy = strategy or NumericMatchStrategy()

    def grade(
        self,
        expected: str,
        actual_answer: str,
        *,
        expected_outcome: Outcome | None = None,
        agent_outcome: Outcome | None = None,
    ) -> Literal["matched", "not_matched", "needs_review"]:
        """Grades one answer. Rules, checked in order (008 contracts/grading.md):

        1. `expected_outcome is None` → the strategy's verdict on `expected`, as before 008.
        2. `agent_outcome != expected_outcome` → `not_matched` (also when `agent_outcome`
           is `None`).
        3. `expected_outcome` is `none` or `needs_clarification` → `not_matched` if the
           answer `contains_amount`, else `matched`. `expected` is ignored.
        4. Otherwise (`full` / `partial`) → the strategy's verdict on `expected`.
        """
        if expected_outcome is None:
            return self._strategy.evaluate(expected, actual_answer)
        if agent_outcome != expected_outcome:
            return "not_matched"
        if expected_outcome in _NO_AMOUNT_OUTCOMES:
            return "not_matched" if contains_amount(actual_answer) else "matched"
        return self._strategy.evaluate(expected, actual_answer)
