"""Unit tests for grounding.ungrounded_figures (008 research.md R11, SC-003)."""

from qa_agent.models import RetrievalStep
from testset_runner.grounding import ungrounded_figures


def _step(summary: str) -> RetrievalStep:
    return RetrievalStep(tool_name="aggregate_rows", arguments={}, result_summary=summary)


def test_a_figure_from_a_step_summary_is_grounded_across_locale_formats() -> None:
    steps = [_step('{"rows": [{"pago": 3816813.0}]}')]
    assert ungrounded_figures("Foram pagos R$ 3.816.813,00.", "Quanto foi pago?", steps) == []


def test_a_year_taken_from_the_message_is_grounded() -> None:
    steps = [_step('{"value": 42}')]
    assert ungrounded_figures("Em 2016, foram pagos R$ 42.", "e em 2016?", steps) == []


def test_a_figure_only_in_an_earlier_answer_is_flagged() -> None:
    steps = [_step('{"value": 42}')]
    answer = "Em 2016 foram pagos R$ 42, contra R$ 1.000 em 2015."
    assert ungrounded_figures(answer, "e em 2016?", steps) == ["1.000", "2015"]


def test_duplicates_are_reported_once_in_first_appearance_order() -> None:
    answer = "Valores: 7, 5, 7 e 5."
    assert ungrounded_figures(answer, "quais?", []) == ["7", "5"]


def test_an_answer_without_numbers_has_nothing_flagged() -> None:
    assert ungrounded_figures("Não há dados sobre isso.", "e em 2016?", []) == []
