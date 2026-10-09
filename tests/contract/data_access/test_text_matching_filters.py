"""Contract tests for forgiving text filters, US1 (specs/009-text-value-matching/contracts/text-matching.md).

Every filter runs through both public capabilities: `query_rows` (matched row indexes) and
`aggregate_rows` (a per-row count grouped by `valor_pago`, which is unique per fixture row),
so the two must agree on the same row set (FR-005). Fixture: `budget_actions.csv`.
"""

from pathlib import Path

import pytest

from data_access.capabilities import aggregate_rows, query_rows
from data_access.dataset import Dataset
from data_access.models import (
    AggregateSpec,
    AggregationRequest,
    ContainsCondition,
    EqualsCondition,
    FilterCondition,
    RangeCondition,
)

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "data_access" / "sample_dataset"
SOURCE = "budget_actions.csv"

AEB = "Agência Espacial Brasileira"
MCTIC = "Ministério da Ciência, Tecnologia, Inovações e Comunicações"
CBERS_3 = "Desenvolvimento do Satélite Sino-Brasileiro - Projeto CBERS-3"
CBERS_4 = "Desenvolvimento do Satélite Sino-Brasileiro - Projeto CBERS-4"
AMAZONIA = "Desenvolvimento do Satélite Amazônia-1"


def _rows(filters: list[FilterCondition]) -> list[dict[str, str | None]]:
    """Rows matched by `query_rows`, checked to equal the rows `aggregate_rows` groups."""
    dataset = Dataset(FIXTURES)
    result = query_rows(dataset, SOURCE, filters)
    assert result.total_match_count == result.returned_count

    aggregated = aggregate_rows(
        dataset,
        SOURCE,
        AggregationRequest(
            group_by=["valor_pago"],
            aggregates=[AggregateSpec(value_field="valor_pago", function="count")],
            filters=filters,
        ),
    )
    assert sorted(g.group_values["valor_pago"] or "" for g in aggregated.groups) == sorted(
        row["valor_pago"] or "" for row in result.rows
    )
    return result.rows


def _values(filters: list[FilterCondition], field: str) -> set[str | None]:
    return {row[field] for row in _rows(filters)}


def _count(filters: list[FilterCondition]) -> int:
    return len(_rows(filters))


def test_us1_as1_equals_ignores_case_and_accents() -> None:
    rows = _rows([EqualsCondition(field="nome_unidade", value="agencia espacial brasileira")])
    assert len(rows) == 22
    assert {row["nome_unidade"] for row in rows} == {AEB}


def test_us1_as2_equals_ignores_hyphen() -> None:
    rows = _rows([EqualsCondition(field="nome_acao", value="projeto cbers 4")])
    assert len(rows) == 3
    assert {row["nome_acao"] for row in rows} == {"Projeto CBERS-4"}


def test_us1_as3_equals_ignores_punctuation_and_accents() -> None:
    value = "Ministerio da Ciencia Tecnologia Inovacoes e Comunicacoes"
    rows = _rows([EqualsCondition(field="nome_unidade", value=value)])
    assert len(rows) == 3
    assert {row["nome_unidade"] for row in rows} == {MCTIC}


def test_us1_as4_contains_skips_stopwords_word_order_and_accents() -> None:
    condition = ContainsCondition(
        field="nome_acao", value="desenvolvimento de satelite sino brasileiro"
    )
    assert _values([condition], "nome_acao") == {CBERS_3, CBERS_4}
    assert _count([condition]) == 7


def test_us1_as5_equals_does_not_match_part_of_a_value() -> None:
    assert _rows([EqualsCondition(field="nome_unidade", value="Agência Espacial")]) == []


def test_us1_as6_range_filter_unchanged() -> None:
    rows = _rows([RangeCondition(field="data_ano", min=2013, max=2014)])
    assert len(rows) == 5
    assert {row["data_ano"] for row in rows} == {"2013", "2014"}


@pytest.mark.parametrize(
    ("field", "value", "count"),
    [
        ("nome_unidade", AEB, 22),
        ("nome_unidade", MCTIC, 3),
        ("nome_acao", CBERS_3, 4),
        ("nome_acao", AMAZONIA, 5),
        ("nome_acao", "Projeto CBERS-4A", 2),
        ("data_ano", "2013", 3),
    ],
)
def test_us1_as7_exact_stored_value_matches_same_rows_as_before(
    field: str, value: str, count: int
) -> None:
    rows = _rows([EqualsCondition(field=field, value=value)])
    assert len(rows) == count
    assert {row[field] for row in rows} == {value}


def test_clarif_q1_contains_word_start_prefix() -> None:
    assert _values([ContainsCondition(field="nome_acao", value="satel")], "nome_acao") == {
        CBERS_3,
        CBERS_4,
        AMAZONIA,
    }


def test_clarif_q1_contains_digit_does_not_match_inside_2014() -> None:
    values = _values([ContainsCondition(field="nome_acao", value="4")], "nome_acao")
    assert "Ação Orçamentária 2014" not in values
    assert "Projeto CBERS-14" not in values
    assert values == {CBERS_4, "Projeto CBERS-4", "Projeto CBERS-4A"}


def test_clarif_q1_contains_cbers_4_excludes_cbers_14_includes_cbers_4a() -> None:
    values = _values([ContainsCondition(field="nome_acao", value="cbers 4")], "nome_acao")
    assert values == {CBERS_4, "Projeto CBERS-4", "Projeto CBERS-4A"}


def test_edge_contains_only_stopwords_matches_word_starts() -> None:
    values = _values([ContainsCondition(field="nome_acao", value="de")], "nome_acao")
    assert values == {CBERS_3, CBERS_4, AMAZONIA}


def test_edge_contains_punctuation_only_matches_every_non_missing_value() -> None:
    rows = _rows([ContainsCondition(field="nome_acao", value="...")])
    assert len(rows) == 23
    assert all((row["nome_acao"] or "").strip() for row in rows)


def test_edge_equals_dash_matches_ellipsis_not_missing() -> None:
    rows = _rows([EqualsCondition(field="nome_acao", value="-")])
    assert [row["nome_acao"] for row in rows] == ["..."]


def test_edge_equals_matches_case_variants() -> None:
    values = _values([EqualsCondition(field="nome_acao", value="programa x")], "nome_acao")
    assert values == {"Programa X", "PROGRAMA X"}


def test_edge_equals_numeric_like_field_unchanged() -> None:
    rows = _rows([EqualsCondition(field="data_ano", value="2012")])
    assert len(rows) == 20


def test_edge_value_with_symbols_matches_itself() -> None:
    for condition in (
        EqualsCondition(field="nome_acao", value="Nº 5 – 10%"),
        ContainsCondition(field="nome_acao", value="Nº 5 – 10%"),
    ):
        assert _values([condition], "nome_acao") == {"Nº 5 – 10%"}


def test_fr006_rows_hold_raw_stored_values() -> None:
    value = "MINISTERIO DA CIENCIA TECNOLOGIA INOVACOES E COMUNICACOES"
    rows = _rows([EqualsCondition(field="nome_unidade", value=value)])
    assert rows[0]["nome_unidade"] == MCTIC
    assert rows[0]["nome_programa"] == "Ciência, Tecnologia e Inovação"


def test_deliberate_change_empty_text_filters_no_longer_match_missing_cells() -> None:
    # Before 009, `equals ""` matched the empty cell and `contains ""` matched every row.
    # Now neither matches "" or "   "; `equals ""` only matches "..." (both normalize to "").
    rows = _rows([EqualsCondition(field="nome_acao", value="")])
    assert [row["nome_acao"] for row in rows] == ["..."]
    assert _count([ContainsCondition(field="nome_acao", value="")]) == 23
