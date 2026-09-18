"""Unit tests for parse_locale_number's per-value locale detection (research.md §3)."""

import pytest

from data_access.numeric import parse_locale_number


class TestPureIntegers:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("1234", 1234.0),
            ("0", 0.0),
            ("-42", -42.0),
        ],
    )
    def test_all_digits_parsed_directly(self, raw: str, expected: float) -> None:
        assert parse_locale_number(raw) == expected


class TestMixedSeparators:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("1.234,56", 1234.56),
            ("1,234.56", 1234.56),
            ("-1.234,56", -1234.56),
            ("1.234.567,89", 1234567.89),
        ],
    )
    def test_rightmost_separator_is_decimal_point(self, raw: str, expected: float) -> None:
        assert parse_locale_number(raw) == pytest.approx(expected)

    def test_inconsistent_grouping_is_unparseable(self) -> None:
        assert parse_locale_number("1.23,456") is None


class TestSingleSeparatorAmbiguousCases:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("1234,56", 1234.56),
            ("1234.5", 1234.5),
            ("1,234", 1234.0),
            ("1.234", 1234.0),
            ("12,345", 12345.0),
        ],
    )
    def test_disambiguated_by_trailing_group_size(self, raw: str, expected: float) -> None:
        assert parse_locale_number(raw) == pytest.approx(expected)

    def test_four_trailing_digits_is_unparseable(self) -> None:
        assert parse_locale_number("1,2345") is None

    def test_inconsistent_grouping_is_unparseable(self) -> None:
        assert parse_locale_number("12,3456") is None


class TestUnparseable:
    @pytest.mark.parametrize("raw", ["", "   ", "abc", "N/A"])
    def test_unparseable_strings_return_none(self, raw: str) -> None:
        assert parse_locale_number(raw) is None
