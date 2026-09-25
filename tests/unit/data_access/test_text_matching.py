"""Unit tests for the pure matching rules (specs/009-text-value-matching/contracts/text-matching.md
and contracts/value-suggestions.md, "Ranking candidates").

Test names carry the scenario id of the contract row they state (US1-AS*, Clarif-Q1, Edge).
"""

import pydantic
import pytest

from data_access.text_matching import (
    MatchRules,
    TextMatchingConfig,
    load_stopwords,
    normalize,
    rank_candidates,
)

RULES = MatchRules.from_config(TextMatchingConfig())

MCTIC = "Ministério da Ciência, Tecnologia, Inovações e Comunicações"


# --- Normalization (FR-001) ------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Agência Espacial Brasileira", "agencia espacial brasileira"),
        ("Projeto CBERS-4", "projeto cbers 4"),
        (MCTIC, "ministerio da ciencia tecnologia inovacoes e comunicacoes"),
        ("  Satélite   Sino-Brasileiro (CBERS) ", "satelite sino brasileiro cbers"),
        ("-", ""),
        ("...", ""),
        ("2012", "2012"),
    ],
)
def test_normalization_table(text: str, expected: str) -> None:
    assert normalize(text) == expected


# --- equals (FR-002) -------------------------------------------------------------------


def test_us1_as1_equals_ignores_case_and_accents() -> None:
    assert RULES.equals("Agência Espacial Brasileira", "agencia espacial brasileira")


def test_us1_as2_equals_ignores_hyphens() -> None:
    assert RULES.equals("Projeto CBERS-4", "projeto cbers 4")


def test_us1_as3_equals_ignores_punctuation_and_accents() -> None:
    assert RULES.equals(MCTIC, "Ministerio da Ciencia Tecnologia Inovacoes e Comunicacoes")


def test_us1_as5_equals_compares_the_whole_value() -> None:
    assert not RULES.equals("Agência Espacial Brasileira", "Agência Espacial")


def test_us1_as7_exact_stored_value_still_equals_itself() -> None:
    assert RULES.equals("Programa X", "Programa X")


def test_edge_equals_does_not_skip_stopwords() -> None:
    assert not RULES.equals("Satélite do Brasil", "Satélite Brasil")


def test_edge_equals_punctuation_only_values_normalize_to_empty() -> None:
    assert RULES.equals("...", "-")


def test_edge_equals_case_variants_both_match() -> None:
    assert RULES.equals("Programa X", "programa x")
    assert RULES.equals("PROGRAMA X", "programa x")


def test_edge_equals_numeric_like_value() -> None:
    assert RULES.equals("2012", "2012")
    assert not RULES.equals("2013", "2012")


def test_edge_value_with_symbols_matches_itself() -> None:
    assert RULES.equals("Nº 5 – 10%", "Nº 5 – 10%")
    assert RULES.contains("Nº 5 – 10%", "Nº 5 – 10%")


# --- contains (FR-003, FR-004) ---------------------------------------------------------


def test_us1_as4_contains_skips_stopwords_and_ignores_word_order_and_accents() -> None:
    stored = "Desenvolvimento do Satélite Sino-Brasileiro - Projeto CBERS-3"
    assert RULES.contains(stored, "desenvolvimento de satelite sino brasileiro")
    assert RULES.contains(stored, "cbers satélite")


def test_clarif_q1_contains_word_start_prefix_matches() -> None:
    assert RULES.contains("Satélite", "satel")


def test_clarif_q1_contains_digit_does_not_match_inside_a_word() -> None:
    assert not RULES.contains("Ação Orçamentária 2014", "4")


def test_clarif_q1_contains_cbers_4_does_not_match_cbers_14() -> None:
    assert not RULES.contains("Projeto CBERS-14", "cbers 4")


def test_edge_contains_cbers_4_matches_cbers_4a() -> None:
    assert RULES.contains("Projeto CBERS-4A", "cbers 4")


def test_edge_contains_only_stopwords_keeps_them() -> None:
    assert RULES.query_words("de") == ["de"]
    assert RULES.contains("Desenvolvimento", "de")


def test_edge_contains_without_query_words_matches_any_value() -> None:
    assert RULES.query_words("...") == []
    assert RULES.contains("Programa X", "...")
    assert RULES.contains("Programa X", "")


def test_existing_contains_al_matches_alice_only() -> None:
    assert RULES.contains("Alice", "AL")
    assert not RULES.contains("Carol", "AL")


def test_query_words_drop_stopwords() -> None:
    assert RULES.query_words("desenvolvimento do satélite") == ["desenvolvimento", "satelite"]


# --- acronym and overlap (FR-009, FR-010) ----------------------------------------------


def test_acronym_of_agency_name() -> None:
    assert RULES.acronym("Agência Espacial Brasileira") == "aeb"


def test_acronym_skips_stopwords() -> None:
    assert RULES.acronym(MCTIC) == "mctic"


def test_acronym_of_punctuation_only_value_is_empty() -> None:
    assert RULES.acronym("...") == ""


def test_us2_as1_overlap_counts_acronym_token() -> None:
    assert RULES.overlap("Agência Espacial Brasileira", "AEB") == 1


def test_us2_as2_overlap_counts_query_words_that_start_a_word() -> None:
    stored = "Desenvolvimento do Satélite Sino-Brasileiro - Projeto CBERS-4"
    assert RULES.overlap(stored, "satélite CBERS 5") == 2
    assert RULES.overlap("Projeto CBERS-3", "satélite CBERS 5") == 1


def test_us2_as5_overlap_zero_when_nothing_shared() -> None:
    assert RULES.overlap("Agência Espacial Brasileira", "zzz") == 0


# --- rank_candidates (FR-011) ----------------------------------------------------------


def test_fr011_rank_orders_by_overlap_then_row_count_then_code_point() -> None:
    value_counts = {
        "Projeto CBERS-3": 9,  # overlap 1
        "Satélite CBERS-4": 1,  # overlap 2
        "b satélite cbers": 3,  # overlap 2
        "a satélite cbers": 3,  # overlap 2
        "Outro": 50,  # overlap 0
    }
    ranked = rank_candidates(value_counts, "satélite CBERS 5", RULES, limit=10)
    assert ranked == [
        ("a satélite cbers", 2, 3),
        ("b satélite cbers", 2, 3),
        ("Satélite CBERS-4", 2, 1),
        ("Projeto CBERS-3", 1, 9),
    ]


def test_fr011_rank_code_point_tie_break_puts_uppercase_first() -> None:
    ranked = rank_candidates({"programa x": 1, "Programa X": 1}, "programa", RULES, limit=5)
    assert [value for value, _, _ in ranked] == ["Programa X", "programa x"]


def test_fr011_rank_keeps_first_limit_candidates() -> None:
    value_counts = {f"cbers {i}": i for i in range(1, 8)}
    ranked = rank_candidates(value_counts, "cbers", RULES, limit=3)
    assert [value for value, _, _ in ranked] == ["cbers 7", "cbers 6", "cbers 5"]


def test_us2_as5_rank_returns_empty_when_nothing_overlaps() -> None:
    assert rank_candidates({"Agência Espacial Brasileira": 3}, "zzz", RULES, limit=5) == []


# --- stopword list and config (FR-004, FR-016) -----------------------------------------


def test_stopwords_pt_v1_are_normalized_on_load() -> None:
    stopwords = load_stopwords("pt_v1")
    assert "a" in stopwords  # from "à" (and "a")
    assert "ate" in stopwords  # from "até"
    assert "de" in stopwords
    assert "" not in stopwords
    assert not any(word.startswith("#") for word in stopwords)


def test_config_defaults() -> None:
    config = TextMatchingConfig()
    assert (config.value_list_threshold, config.max_suggestions, config.stopwords) == (
        30,
        5,
        "pt_v1",
    )


@pytest.mark.parametrize("name", ["nope", "../pt_v1", "pt_v1.txt"])
def test_config_rejects_unknown_stopword_list(name: str) -> None:
    with pytest.raises(pydantic.ValidationError):
        TextMatchingConfig(stopwords=name)


def test_config_rejects_zero_max_suggestions() -> None:
    with pytest.raises(pydantic.ValidationError):
        TextMatchingConfig(max_suggestions=0)


def test_config_rejects_negative_threshold() -> None:
    with pytest.raises(pydantic.ValidationError):
        TextMatchingConfig(value_list_threshold=-1)


def test_config_threshold_zero_is_valid() -> None:
    assert TextMatchingConfig(value_list_threshold=0).value_list_threshold == 0
