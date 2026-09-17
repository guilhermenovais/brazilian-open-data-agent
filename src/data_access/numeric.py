"""Per-value locale-aware numeric parsing (research.md §3).

Numeric fields in this dataset may mix Brazilian-style ("1.234,56") and US-style
("1,234.56") formatting within the same field, row to row. There is no per-field or
per-source locale setting: `parse_locale_number` is applied independently to every
single value, detecting its own locale convention from its own separator pattern.
"""

import re

_ALL_DIGITS = re.compile(r"^-?\d+$")
_GROUP_OF_3 = re.compile(r"^\d{1,3}(?:\d{3})*$")

NUMERIC_LIKE_THRESHOLD = 0.8


def parse_locale_number(raw: str) -> float | None:
    value = raw.strip()
    if not value:
        return None

    if _ALL_DIGITS.match(value):
        return float(value)

    has_comma = "," in value
    has_dot = "." in value

    if has_comma and has_dot:
        return _parse_mixed_separators(value)
    if has_comma:
        return _parse_single_separator(value, decimal_sep=",", grouping_sep=".")
    if has_dot:
        return _parse_single_separator(value, decimal_sep=".", grouping_sep=",")
    return None


def _parse_mixed_separators(value: str) -> float | None:
    last_comma = value.rfind(",")
    last_dot = value.rfind(".")
    if last_comma > last_dot:
        decimal_sep, grouping_sep = ",", "."
    else:
        decimal_sep, grouping_sep = ".", ","

    decimal_pos = value.rfind(decimal_sep)
    integer_part = value[:decimal_pos]
    fractional_part = value[decimal_pos + 1 :]

    if not fractional_part.isdigit():
        return None
    if grouping_sep in fractional_part:
        return None

    if not _has_valid_grouping(integer_part, grouping_sep):
        return None

    normalized_integer = integer_part.replace(grouping_sep, "")
    sign = "-" if normalized_integer.startswith("-") else ""
    digits = normalized_integer.lstrip("-")
    if not digits.isdigit():
        return None

    return float(f"{sign}{digits}.{fractional_part}")


def _has_valid_grouping(integer_part: str, grouping_sep: str) -> bool:
    body = integer_part[1:] if integer_part.startswith("-") else integer_part
    if not body:
        return False
    groups = body.split(grouping_sep)
    if any(g == "" for g in groups):
        return False
    if not groups[0].isdigit() or not (1 <= len(groups[0]) <= 3):
        return False
    for g in groups[1:]:
        if not g.isdigit() or len(g) != 3:
            return False
    return True


def is_numeric_like(values: list[str | None]) -> bool:
    """A field is `numeric_like` when >= NUMERIC_LIKE_THRESHOLD of its non-null
    sampled values parse via `parse_locale_number` (research.md §4)."""
    non_null = [v for v in values if v is not None]
    if not non_null:
        return False
    parsed = sum(1 for v in non_null if parse_locale_number(v) is not None)
    return (parsed / len(non_null)) >= NUMERIC_LIKE_THRESHOLD


def _parse_single_separator(value: str, *, decimal_sep: str, grouping_sep: str) -> float | None:
    sign = ""
    body = value
    if body.startswith("-"):
        sign = "-"
        body = body[1:]
    if not body:
        return None

    groups = body.split(decimal_sep)
    last_group = groups[-1]

    if len(groups) >= 2 and 1 <= len(last_group) <= 2 and last_group.isdigit():
        integer_groups = groups[:-1]
        integer_part = "".join(integer_groups)
        if not integer_part.isdigit():
            return None
        return float(f"{sign}{integer_part}.{last_group}")

    normalized = body.replace(decimal_sep, "")
    if _has_valid_grouping(body, decimal_sep) and _ALL_DIGITS.match(normalized):
        return float(f"{sign}{normalized}")

    return None
