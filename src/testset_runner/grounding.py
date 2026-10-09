"""ungrounded_figures: the SC-003 screen for figures an answer did not retrieve this turn
(008 research.md R11).

A figure in the answer is grounded when its value equals a number in the current user
message or in any of the **current turn's** retrieval results. Everything else is
returned. The result is reported, never scored: a value the agent legitimately computed
(e.g. a difference between two retrieved sums) is a known false positive, so each flagged
figure gets a recorded `derived` / `ungrounded` verdict instead
(contracts/conversation-testset.md "Resolving flagged figures").
"""

from data_access.numeric import parse_locale_number
from qa_agent.models import RetrievalStep
from testset_runner.matcher import NUMERIC_SUBSTRING


def ungrounded_figures(answer: str, message: str, steps: list[RetrievalStep]) -> list[str]:
    """Numeric substrings of `answer` (first-appearance order, no duplicates) whose value
    appears in neither `message` nor any `step.result_summary`. Unparseable substrings are
    ignored."""
    grounded: set[float] = set()
    for text in [message, *(step.result_summary for step in steps)]:
        grounded.update(_values(text))

    flagged: list[str] = []
    for match in NUMERIC_SUBSTRING.finditer(answer):
        figure = match.group()
        value = parse_locale_number(figure)
        if value is None or value in grounded or figure in flagged:
            continue
        flagged.append(figure)
    return flagged


def _values(text: str) -> set[float]:
    values: set[float] = set()
    for match in NUMERIC_SUBSTRING.finditer(text):
        value = parse_locale_number(match.group())
        if value is not None:
            values.add(value)
    return values
