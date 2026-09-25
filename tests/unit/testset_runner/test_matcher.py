"""Unit tests for DeterministicMatcher/NumericMatchStrategy (research.md §5)."""

from testset_runner.matcher import DeterministicMatcher


def test_exact_numeric_match_normalizes_brazilian_currency_formatting() -> None:
    matcher = DeterministicMatcher()
    assert matcher.grade("8351", "O valor pago foi de R$ 8.351,00.") == "matched"


def test_exact_numeric_mismatch_is_not_matched() -> None:
    matcher = DeterministicMatcher()
    assert matcher.grade("8351", "O valor pago foi de R$ 9.000,00.") == "not_matched"


def test_us_style_thousands_and_decimal_separators_are_normalized() -> None:
    matcher = DeterministicMatcher()
    assert matcher.grade("1234.56", "The total was 1,234.56 dollars.") == "matched"


def test_tolerant_marker_allows_small_relative_difference() -> None:
    matcher = DeterministicMatcher()
    assert matcher.grade("~3675300.51", "O total aproximado foi de R$ 3.675.300,50.") == "matched"


def test_tolerant_marker_still_rejects_a_large_difference() -> None:
    matcher = DeterministicMatcher()
    assert matcher.grade("~3675300.51", "O total aproximado foi de R$ 1.000.000,00.") == "not_matched"


def test_bare_name_expected_is_always_needs_review() -> None:
    matcher = DeterministicMatcher()
    assert (
        matcher.grade("Agência Espacial Brasileira", "A unidade é a Agência Espacial Brasileira.")
        == "needs_review"
    )


def test_composite_slash_joined_expected_is_always_needs_review() -> None:
    matcher = DeterministicMatcher()
    result = matcher.grade(
        "Agência Espacial Brasileira / Apoio Administrativo / 238959",
        "A unidade é a Agência Espacial Brasileira, o programa é Apoio Administrativo, "
        "valor R$ 238.959,00.",
    )
    assert result == "needs_review"


def test_descriptive_text_expected_is_always_needs_review() -> None:
    matcher = DeterministicMatcher()
    result = matcher.grade(
        "Data not available (no such action/category in the dataset)",
        "Não há dados de merenda escolar para a AEB em 2005.",
    )
    assert result == "needs_review"


# --- 008: contains_amount and outcome-aware grading (contracts/grading.md) ---------------

import pytest  # noqa: E402

from testset_runner.matcher import contains_amount  # noqa: E402

_OUTCOMES = ("full", "partial", "none", "needs_clarification")

# Every case above, as (expected, answer, status) — US3-5 re-grades them all.
_PRE_008_CASES = [
    ("8351", "O valor pago foi de R$ 8.351,00.", "matched"),
    ("8351", "O valor pago foi de R$ 9.000,00.", "not_matched"),
    ("1234.56", "The total was 1,234.56 dollars.", "matched"),
    ("~3675300.51", "O total aproximado foi de R$ 3.675.300,50.", "matched"),
    ("~3675300.51", "O total aproximado foi de R$ 1.000.000,00.", "not_matched"),
    ("Agência Espacial Brasileira", "A unidade é a Agência Espacial Brasileira.", "needs_review"),
    (
        "Agência Espacial Brasileira / Apoio Administrativo / 238959",
        "A unidade é a Agência Espacial Brasileira, o programa é Apoio Administrativo, "
        "valor R$ 238.959,00.",
        "needs_review",
    ),
    (
        "Data not available (no such action/category in the dataset)",
        "Não há dados de merenda escolar para a AEB em 2005.",
        "needs_review",
    ),
]


@pytest.mark.parametrize(
    "text",
    ["R$ 42", "R$42.750,00", "R$ -5", "1.234", "12,5", "206.805.295", "0,36", "36%", "12,5 %"],
)
def test_008_contains_amount_matches(text: str) -> None:
    assert contains_amount(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "R$",
        "2005",
        "em 2005.",
        "2005, 2006",
        "1. Valor pago",
        "2) Valor empenhado",
        "2008 a 2012",
        "Amazônia-1",
        "CBERS-3",
        "por cento",
    ],
)
def test_008_contains_amount_ignores(text: str) -> None:
    assert contains_amount(text) is False


def test_008_us3_1_none_expected_none_reported_no_amount_matches() -> None:
    status = DeterministicMatcher().grade(
        "Data not available",
        "Não há dados para 2020 sobre o Amazônia-1.",
        expected_outcome="none",
        agent_outcome="none",
    )
    assert status == "matched"


def test_008_us3_2_none_expected_partial_reported_not_matched() -> None:
    status = DeterministicMatcher().grade(
        "Data not available",
        "Não há dados para 2020 sobre o Amazônia-1.",
        expected_outcome="none",
        agent_outcome="partial",
    )
    assert status == "not_matched"


def test_008_us3_3_clarification_with_amount_not_matched() -> None:
    status = DeterministicMatcher().grade(
        "Ambiguous",
        "O valor autorizado foi R$ 206.805.295. Você quer o valor pago?",
        expected_outcome="needs_clarification",
        agent_outcome="needs_clarification",
    )
    assert status == "not_matched"


def test_008_us3_4_full_expected_checks_outcome_then_number() -> None:
    matcher = DeterministicMatcher()
    answer = "A dotação foi de R$ 65.000,00."
    assert matcher.grade("65000", answer, expected_outcome="full", agent_outcome="full") == "matched"
    assert (
        matcher.grade("65000", answer, expected_outcome="full", agent_outcome="partial")
        == "not_matched"
    )


@pytest.mark.parametrize("expected,answer,status", _PRE_008_CASES)
def test_008_us3_5_no_expected_outcome_grades_as_before(
    expected: str, answer: str, status: str
) -> None:
    matcher = DeterministicMatcher()
    assert matcher.grade(expected, answer) == status
    for agent_outcome in _OUTCOMES:
        assert (
            matcher.grade(expected, answer, expected_outcome=None, agent_outcome=agent_outcome)
            == status
        )


def test_008_none_expected_with_agent_outcome_none_value_missing_is_not_matched() -> None:
    status = DeterministicMatcher().grade(
        "Data not available", "Não há dados.", expected_outcome="none", agent_outcome=None
    )
    assert status == "not_matched"


def test_008_full_expected_non_numeric_text() -> None:
    matcher = DeterministicMatcher()
    expected = "Agência Espacial Brasileira"
    answer = "A unidade é a Agência Espacial Brasileira."
    assert (
        matcher.grade(expected, answer, expected_outcome="full", agent_outcome="full")
        == "needs_review"
    )
    assert (
        matcher.grade(expected, answer, expected_outcome="full", agent_outcome="none")
        == "not_matched"
    )


def test_008_expected_text_ignored_for_none_and_clarification() -> None:
    matcher = DeterministicMatcher()
    answer = "Você quer saber o valor autorizado ou o valor pago?"
    for outcome in ("none", "needs_clarification"):
        assert (
            matcher.grade("206805295", answer, expected_outcome=outcome, agent_outcome=outcome)
            == "matched"
        )
