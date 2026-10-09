"""Contract tests for schema inspection, US2.1-US2.5 (contracts/inspection.md)."""

from pathlib import Path

import pytest

from data_access.capabilities import SAMPLE_SIZE_CAP, inspect_schema
from data_access.dataset import Dataset
from data_access.exceptions import DataSourceNotFoundError, UnreadableSourceError
from data_access.models import FieldInfo
from data_access.text_matching import TextMatchingConfig

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "data_access" / "sample_dataset"


def test_us2_1_large_csv_capped_sample_all_field_names(tmp_path: Path) -> None:
    lines = ["id,value"] + [f"{i},{i * 10}" for i in range(10_000)]
    (tmp_path / "big.csv").write_text("\n".join(lines) + "\n")
    dataset = Dataset(tmp_path)

    result = inspect_schema(dataset, "big.csv")

    assert {f.name for f in result.fields} == {"id", "value"}
    assert len(result.sample) == SAMPLE_SIZE_CAP


def test_us2_2_heterogeneous_json_union_of_fields() -> None:
    dataset = Dataset(FIXTURES)
    result = inspect_schema(dataset, "products.json")
    field_names = {f.name for f in result.fields}
    assert field_names == {"id", "name", "price", "category"}


def test_us2_3_brazilian_formatted_value_shown_unchanged_and_numeric_like() -> None:
    dataset = Dataset(FIXTURES)
    result = inspect_schema(dataset, "orders/2024/sales.csv")
    amount_field = next(f for f in result.fields if f.name == "amount")
    assert amount_field.type == "numeric_like"
    assert any(row.get("amount") == "1.234,56" for row in result.sample)


def test_us2_4_unknown_identifier_raises_not_found() -> None:
    dataset = Dataset(FIXTURES)
    with pytest.raises(DataSourceNotFoundError):
        inspect_schema(dataset, "does-not-exist.csv")


def test_us2_5_unreadable_source_raises() -> None:
    dataset = Dataset(FIXTURES)
    with pytest.raises(UnreadableSourceError):
        inspect_schema(dataset, "broken.csv")


# --- 009 US3: low-cardinality value lists (specs/009-text-value-matching/contracts/schema-inspection.md)

BUDGET = "budget_actions.csv"
PROGRAMS = [
    "Ciência, Tecnologia e Inovação",
    "Gestão e Manutenção",
    "Política Espacial",
    "Programa Espacial Brasileiro",
]


def _budget_fields(config: TextMatchingConfig = TextMatchingConfig()) -> dict[str, FieldInfo]:
    result = inspect_schema(Dataset(FIXTURES), BUDGET, text_matching=config)
    return {f.name: f for f in result.fields}


def test_009_us3_as1_value_outside_the_sample_is_listed() -> None:
    result = inspect_schema(Dataset(FIXTURES), BUDGET)
    assert {row["nome_unidade"] for row in result.sample} == {"Agência Espacial Brasileira"}
    fields = {f.name: f for f in result.fields}
    assert fields["nome_unidade"].values == [
        "Agência Espacial Brasileira",
        "Ministério da Ciência, Tecnologia, Inovações e Comunicações",
    ]
    assert fields["data_ano"].values == ["2012", "2013", "2014"]


def test_009_us3_as2_exactly_threshold_values_all_listed_in_code_point_order() -> None:
    field = _budget_fields(TextMatchingConfig(value_list_threshold=4))["nome_programa"]
    assert field.distinct_count == 4
    assert field.values == PROGRAMS


def test_009_us3_as3_threshold_plus_one_values_not_listed() -> None:
    field = _budget_fields(TextMatchingConfig(value_list_threshold=3))["nome_programa"]
    assert field.values is None
    assert field.distinct_count == 4


def test_009_us3_as4_missing_cells_neither_listed_nor_counted() -> None:
    field = _budget_fields()["nome_acao"]
    assert field.distinct_count == 11
    assert field.values is not None
    assert all(value.strip() for value in field.values)


def test_009_us3_as5_existing_output_unchanged() -> None:
    result = inspect_schema(Dataset(FIXTURES), "customers.csv")
    assert result.identifier == "customers.csv"
    assert [(f.name, f.type) for f in result.fields] == [
        ("id", "numeric_like"),
        ("name", "text"),
        ("balance", "numeric_like"),
    ]
    assert result.sample == [
        {"id": "1", "name": "Alice", "balance": "1,234.56"},
        {"id": "2", "name": "Bob", "balance": "2,500.00"},
        {"id": "3", "name": "Carol", "balance": "999.99"},
        {"id": "4", "name": "Dave", "balance": "10,000.00"},
    ]
    assert result.fields[1].values == ["Alice", "Bob", "Carol", "Dave"]


def test_009_edge_case_variants_are_two_entries() -> None:
    values = _budget_fields()["nome_acao"].values
    assert values is not None
    assert "Programa X" in values and "PROGRAMA X" in values


def test_009_edge_threshold_zero_lists_nothing() -> None:
    fields = _budget_fields(TextMatchingConfig(value_list_threshold=0))
    assert all(f.values is None for f in fields.values())
    assert all(f.distinct_count > 0 for f in fields.values())


@pytest.mark.parametrize("threshold", [0, 3, 4, 11, 30])
def test_009_invariants_values_listed_iff_within_threshold(threshold: int) -> None:
    result = inspect_schema(
        Dataset(FIXTURES), BUDGET, text_matching=TextMatchingConfig(value_list_threshold=threshold)
    )
    assert result.value_list_threshold == threshold
    for field in result.fields:
        assert (field.values is None) == (field.distinct_count > threshold)
        if field.values is not None:
            assert len(field.values) == field.distinct_count
            assert field.values == sorted(field.values)
