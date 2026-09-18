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
