"""Contract tests for US1 Acceptance Scenarios 1-3 (contracts/answering.md).

Uses pydantic_ai.models.function.FunctionModel against the real
data/briefings/orcamentos-aeb-csv.md briefing and data/datasets/orcamentos-aeb-csv
dataset (mirroring tests/contract/dataset_selector/test_selection.py's
REPO_ROOT/real-fixture pattern), driving the full answer_question flow via the
private `_answer_with_selection` model-override seam (capabilities.py) so the run log
write (FR-013) and outcome clamp are exercised for real, not just the raw Agent.
"""

import json
from pathlib import Path

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from data_access.capabilities import aggregate_rows as real_aggregate_rows
from data_access.dataset import Dataset
from data_access.models import AggregateSpec, AggregationRequest
from dataset_selector.briefing import FileBriefingSource
from dataset_selector.capabilities import select_dataset
from dataset_selector.locator import LocalDatasetLocator
from dataset_selector.selector import StaticDatasetSelector
from dataset_selector.usage_log import JsonlSelectionLogger
from qa_agent.capabilities import _answer_with_selection
from qa_agent.run_log import JsonlRunLogger
from qa_agent.settings import AgentSettings

REPO_ROOT = Path(__file__).parent.parent.parent.parent
BRIEFINGS_ROOT = REPO_ROOT / "data" / "briefings"
DATASETS_ROOT = REPO_ROOT / "data" / "datasets"
DATASET_KEY = "orcamentos-aeb-csv"
SOURCE_IDENTIFIER = "dados_gerais/tb_geral.csv"
AEB_UNIT_NAME = "Agência Espacial Brasileira"
QUESTION_YEAR = "2013"


def _real_dataset() -> Dataset:
    return Dataset(DATASETS_ROOT / DATASET_KEY)


def _real_selector() -> StaticDatasetSelector:
    return StaticDatasetSelector(
        briefing_source=FileBriefingSource(BRIEFINGS_ROOT),
        locator=LocalDatasetLocator(DATASETS_ROOT),
    )


def _expected_sum(value_field: str) -> float:
    """Independently computed real value, via the same capability the agent's tool wraps."""
    result = real_aggregate_rows(
        _real_dataset(),
        SOURCE_IDENTIFIER,
        AggregationRequest(
            group_by=["nome_unidade", "data_ano"],
            aggregates=[AggregateSpec(value_field=value_field, function="sum")],
        ),
    )
    matched = next(
        g
        for g in result.groups
        if g.group_values.get("nome_unidade") == AEB_UNIT_NAME
        and g.group_values.get("data_ano") == QUESTION_YEAR
    )
    return matched.results[f"sum_{value_field}"]


def _scripted_single_aggregate(value_field: str, answer_text: str):
    """A FunctionModel script: aggregate once, then answer using the real retrieved value."""

    def scripted(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if len(messages) == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="aggregate_rows",
                        args={
                            "identifier": SOURCE_IDENTIFIER,
                            "request": {
                                "group_by": ["nome_unidade", "data_ano"],
                                "aggregates": [{"value_field": value_field, "function": "sum"}],
                            },
                        },
                    )
                ]
            )
        last_request = messages[-1]
        tool_return = next(p for p in last_request.parts if isinstance(p, ToolReturnPart))
        matched = next(
            g
            for g in tool_return.content.groups
            if g.group_values.get("nome_unidade") == AEB_UNIT_NAME
            and g.group_values.get("data_ano") == QUESTION_YEAR
        )
        value = matched.results[f"sum_{value_field}"]
        return ModelResponse(
            parts=[TextPart(json.dumps({"answer": answer_text.format(value=value), "outcome": "full"}))]
        )

    return scripted


def _answer(question: str, model, tmp_path: Path):
    selector = _real_selector()
    selection = select_dataset(
        question, selector=selector, logger=JsonlSelectionLogger(tmp_path / "selections.jsonl")
    )
    run_logger = JsonlRunLogger(tmp_path / "runs.jsonl")
    result = _answer_with_selection(
        question,
        selection,
        run_logger=run_logger,
        settings=AgentSettings(model_name="test", instrument=False),
        model_override=model,
    )
    return result, tmp_path / "runs.jsonl"


def test_as1_grounded_single_fact_answer_matches_real_data(tmp_path: Path) -> None:
    expected = _expected_sum("pago")
    scripted = _scripted_single_aggregate("pago", "O valor pago pela AEB em 2013 foi de R$ {value}.")

    result, _ = _answer("Quanto foi pago pela AEB em 2013?", FunctionModel(scripted), tmp_path)

    assert result.outcome == "full"
    assert str(expected) in result.answer


def test_as2_everyday_synonym_resolves_to_same_correct_value(tmp_path: Path) -> None:
    expected = _expected_sum("empenhado")
    scripted = _scripted_single_aggregate(
        "empenhado", "O valor gasto (empenhado) pela AEB em 2013 foi de R$ {value}."
    )

    result, _ = _answer("Quanto foi gasto pela AEB em 2013?", FunctionModel(scripted), tmp_path)

    assert result.outcome == "full"
    assert str(expected) in result.answer


def test_as3_answer_never_leaks_internal_identifiers(tmp_path: Path) -> None:
    scripted = _scripted_single_aggregate("pago", "O valor pago pela AEB em 2013 foi de R$ {value}.")

    result, _ = _answer("Quanto foi pago pela AEB em 2013?", FunctionModel(scripted), tmp_path)

    answer_lower = result.answer.lower()
    assert "tb_geral.csv" not in answer_lower
    assert DATASET_KEY not in answer_lower
    assert "nome_unidade" not in answer_lower
    assert "data_ano" not in answer_lower


def test_fr013_exactly_one_log_entry_written_per_call(tmp_path: Path) -> None:
    scripted = _scripted_single_aggregate("pago", "O valor pago pela AEB em 2013 foi de R$ {value}.")

    result, log_path = _answer("Quanto foi pago pela AEB em 2013?", FunctionModel(scripted), tmp_path)

    assert result.outcome == "full"
    lines = log_path.read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["question"] == "Quanto foi pago pela AEB em 2013?"
    assert entry["dataset_key"] == DATASET_KEY
    assert entry["outcome"] == "full"
