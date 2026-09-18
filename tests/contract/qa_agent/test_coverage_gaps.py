"""Contract tests for US2 Acceptance Scenarios 1-4 (contracts/answering.md).

Uses FunctionModel against the real dataset/briefing, driving the full
answer_question flow via the private `_answer_with_selection` model-override seam
(capabilities.py) — see test_grounded_answers.py's module docstring for why.
"""

import json
from pathlib import Path

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

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


def _real_selector() -> StaticDatasetSelector:
    return StaticDatasetSelector(
        briefing_source=FileBriefingSource(BRIEFINGS_ROOT),
        locator=LocalDatasetLocator(DATASETS_ROOT),
    )


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


def _scripted_immediate_decline(answer_text: str):
    """Model recognizes the question is out of coverage without calling any tool."""

    def scripted(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(
            parts=[TextPart(json.dumps({"answer": answer_text, "outcome": "none"}))]
        )

    return scripted


def test_as1_wrong_subject_declines_with_no_invented_figure(tmp_path: Path) -> None:
    scripted = _scripted_immediate_decline(
        "Não é possível responder: esta base de dados cobre apenas a AEB e o MCTIC, "
        "não o Ministério da Saúde."
    )

    result, log_path = _answer(
        "Quanto o Ministério da Saúde gastou em 2015?", FunctionModel(scripted), tmp_path
    )

    assert result.outcome == "none"
    assert "R$" not in result.answer
    entry = json.loads(log_path.read_text().splitlines()[0])
    assert entry["outcome"] == "none"


def test_as2_out_of_range_year_declines_without_extrapolation(tmp_path: Path) -> None:
    scripted = _scripted_immediate_decline(
        "Não é possível responder: esta base de dados cobre apenas os anos de 2000 a 2019."
    )

    result, _ = _answer("Quanto foi pago pela AEB em 2021?", FunctionModel(scripted), tmp_path)

    assert result.outcome == "none"
    assert "R$" not in result.answer


def test_as3_untracked_granularity_declines_without_approximation(tmp_path: Path) -> None:
    scripted = _scripted_immediate_decline(
        "Não é possível responder: esta base de dados não possui detalhamento mensal, "
        "apenas totais anuais."
    )

    result, _ = _answer(
        "Quanto a AEB pagou por mês em 2010?", FunctionModel(scripted), tmp_path
    )

    assert result.outcome == "none"
    assert "R$" not in result.answer


def test_as4_partially_covered_question_states_covered_fact_and_gap(tmp_path: Path) -> None:
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
                                "aggregates": [{"value_field": "pago", "function": "sum"}],
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
            if g.group_values.get("nome_unidade") == "Agência Espacial Brasileira"
            and g.group_values.get("data_ano") == "2013"
        )
        value = matched.results["sum_pago"]
        answer = (
            f"O valor pago pela AEB em 2013 foi de R$ {value}. Não foi possível informar "
            "o detalhamento por fornecedor, pois esta base de dados não possui esse nível "
            "de detalhe."
        )
        return ModelResponse(parts=[TextPart(json.dumps({"answer": answer, "outcome": "partial"}))])

    result, log_path = _answer(
        "Quanto foi pago pela AEB em 2013 e para quais fornecedores?",
        FunctionModel(scripted),
        tmp_path,
    )

    assert result.outcome == "partial"
    assert "não foi possível" in result.answer.lower()
    entry = json.loads(log_path.read_text().splitlines()[0])
    assert entry["outcome"] == "partial"
