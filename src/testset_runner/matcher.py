"""MatchStrategy/DeterministicMatcher: deterministic auto-grading of numeric answers
(research.md §5, Constitution Principle VI).

Any `expected` value that does not itself parse as a number is always `needs_review`
— never auto-guessed, regardless of how the agent's free-text answer reads.
"""

import re
from typing import Literal, Protocol

from data_access.numeric import parse_locale_number

# Public so `grounding.py` finds figures in an answer with exactly the same rule.
NUMERIC_SUBSTRING = re.compile(r"-?\d[\d.,]*\d|-?\d")
_APPROXIMATE_RELATIVE_TOLERANCE = 0.01


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
        self, expected: str, actual_answer: str
    ) -> Literal["matched", "not_matched", "needs_review"]:
        return self._strategy.evaluate(expected, actual_answer)
