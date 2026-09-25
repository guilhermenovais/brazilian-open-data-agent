"""Contract tests for value suggestions on empty results, US2
(specs/009-text-value-matching/contracts/value-suggestions.md). Fixture: `budget_actions.csv`.
"""

from pathlib import Path

from data_access.capabilities import aggregate_rows, query_rows
from data_access.dataset import Dataset
from data_access.models import (
    AggregateSpec,
    AggregationRequest,
    ContainsCondition,
    EqualsCondition,
    FilterCondition,
    RangeCondition,
    ValueSuggestion,
)
from data_access.text_matching import TextMatchingConfig

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "data_access" / "sample_dataset"
SOURCE = "budget_actions.csv"

AEB = "Agência Espacial Brasileira"
MCTIC = "Ministério da Ciência, Tecnologia, Inovações e Comunicações"
CBERS_3 = "Desenvolvimento do Satélite Sino-Brasileiro - Projeto CBERS-3"
CBERS_4 = "Desenvolvimento do Satélite Sino-Brasileiro - Projeto CBERS-4"


def _suggestions(
    filters: list[FilterCondition], config: TextMatchingConfig = TextMatchingConfig()
) -> list[ValueSuggestion] | None:
    result = query_rows(Dataset(FIXTURES), SOURCE, filters, text_matching=config)
    assert result.total_match_count == 0
    return result.value_suggestions


def _candidate_values(suggestion: ValueSuggestion) -> list[str]:
    return [c.value for c in suggestion.candidates]


def test_us2_as1_acronym_suggests_the_full_name_first() -> None:
    suggestions = _suggestions([EqualsCondition(field="nome_unidade", value="AEB")])
    assert suggestions is not None and len(suggestions) == 1
    first = suggestions[0].candidates[0]
    assert (first.value, first.overlap, first.row_count) == (AEB, 1, 22)


def test_us2_as2_candidates_ordered_by_overlap() -> None:
    suggestions = _suggestions([ContainsCondition(field="nome_acao", value="satélite CBERS 5")])
    assert suggestions is not None
    candidates = suggestions[0].candidates
    overlaps = [c.overlap for c in candidates]
    assert overlaps == sorted(overlaps, reverse=True)
    values = _candidate_values(suggestions[0])
    assert values.index(CBERS_4) < values.index("Projeto CBERS-4")
    assert {c.value for c in candidates if c.overlap == 2} == {CBERS_3, CBERS_4}


def test_us2_as3_only_the_condition_that_matches_nothing_gets_an_entry() -> None:
    suggestions = _suggestions(
        [
            EqualsCondition(field="nome_unidade", value=AEB),
            EqualsCondition(field="nome_acao", value="Projeto CBERS-9"),
        ]
    )
    assert suggestions is not None
    assert [(s.field, s.value) for s in suggestions] == [("nome_acao", "Projeto CBERS-9")]


def test_us2_as4_every_condition_matches_alone_gives_empty_list() -> None:
    filters: list[FilterCondition] = [
        EqualsCondition(field="nome_unidade", value=MCTIC),
        EqualsCondition(field="nome_acao", value="Programa X"),
    ]
    assert _suggestions(filters) == []
    result = query_rows(Dataset(FIXTURES), SOURCE, filters)
    assert '"value_suggestions":[]' in result.model_dump_json()


def test_us2_as5_no_shared_word_gives_entry_with_no_candidates() -> None:
    suggestions = _suggestions([EqualsCondition(field="nome_unidade", value="zzz")])
    assert suggestions is not None and len(suggestions) == 1
    assert suggestions[0].candidates == []


def test_us2_as6_non_empty_result_has_no_suggestions_key() -> None:
    matched = query_rows(
        Dataset(FIXTURES), SOURCE, [EqualsCondition(field="nome_unidade", value=AEB)]
    )
    assert matched.total_match_count > 0
    assert matched.value_suggestions is None
    assert "value_suggestions" not in matched.model_dump_json()

    aggregated = aggregate_rows(
        Dataset(FIXTURES),
        SOURCE,
        AggregationRequest(
            group_by=["nome_unidade"],
            aggregates=[AggregateSpec(value_field="nome_unidade", function="count")],
        ),
    )
    assert aggregated.total_group_count > 0
    assert "value_suggestions" not in aggregated.model_dump_json()


def test_us2_as7_range_only_empty_result_has_no_suggestions_key() -> None:
    result = query_rows(
        Dataset(FIXTURES), SOURCE, [RangeCondition(field="data_ano", min=1990, max=1999)]
    )
    assert result.total_match_count == 0
    assert result.value_suggestions is None
    assert "value_suggestions" not in result.model_dump_json()


def test_fr011_at_most_max_suggestions_ties_by_row_count_then_code_point() -> None:
    # "projeto cbers 9" overlaps 2 with five values: CBERS-3 (4 rows), CBERS-4 (3 rows),
    # "Projeto CBERS-4" (3 rows), "Projeto CBERS-4A" (2 rows), "Projeto CBERS-14" (1 row).
    condition = ContainsCondition(field="nome_acao", value="projeto cbers 9")
    limited = _suggestions([condition], TextMatchingConfig(max_suggestions=2))
    assert limited is not None
    assert [(c.value, c.overlap, c.row_count) for c in limited[0].candidates] == [
        (CBERS_3, 2, 4),
        (CBERS_4, 2, 3),
    ]

    full = _suggestions([condition])
    assert full is not None
    assert _candidate_values(full[0]) == [
        CBERS_3,
        CBERS_4,
        "Projeto CBERS-4",
        "Projeto CBERS-4A",
        "Projeto CBERS-14",
    ]


def test_fr012_entry_carries_field_op_and_value_as_sent() -> None:
    suggestions = _suggestions(
        [ContainsCondition(field="nome_programa", value="Programa Espacial Chinês")]
    )
    assert suggestions is not None
    entry = suggestions[0]
    assert (entry.field, entry.op, entry.value) == (
        "nome_programa",
        "contains",
        "Programa Espacial Chinês",
    )


def test_fr006_candidates_are_raw_stored_spellings() -> None:
    suggestions = _suggestions([EqualsCondition(field="nome_acao", value="programa y")])
    assert suggestions is not None
    assert set(_candidate_values(suggestions[0])) >= {"Programa X", "PROGRAMA X"}


def test_edge_missing_values_are_never_candidates() -> None:
    suggestions = _suggestions([EqualsCondition(field="nome_acao", value="projeto")])
    assert suggestions is not None
    values = _candidate_values(suggestions[0])
    assert values
    assert all(value.strip() for value in values)


def test_edge_aggregate_rows_with_zero_groups_gives_same_entries_as_query_rows() -> None:
    filters: list[FilterCondition] = [
        EqualsCondition(field="nome_unidade", value="AEB"),
        ContainsCondition(field="nome_acao", value="satélite CBERS 5"),
        RangeCondition(field="data_ano", min=2012, max=2012),
    ]
    aggregated = aggregate_rows(
        Dataset(FIXTURES),
        SOURCE,
        AggregationRequest(
            group_by=["nome_acao"],
            aggregates=[AggregateSpec(value_field="valor_pago", function="sum")],
            filters=filters,
            limit=1,
        ),
    )
    assert aggregated.total_group_count == 0
    assert aggregated.value_suggestions == _suggestions(filters)
    assert aggregated.value_suggestions is not None
    assert [s.field for s in aggregated.value_suggestions] == ["nome_unidade", "nome_acao"]
