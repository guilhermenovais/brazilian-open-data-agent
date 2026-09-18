"""Contract tests for US3 Acceptance Scenarios 1-3 (contracts/answering.md).

Uses FunctionModel-scripted multi-tool-call sequences against the real dataset,
driving the full answer_question flow via the private `_answer_with_selection`
model-override seam (capabilities.py) — see test_grounded_answers.py's module
docstring for why, and `capture_deps` to inspect `step_budget.attempts` afterward.
"""

import json
from pathlib import Path

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from data_access.capabilities import query_rows as real_query_rows
from data_access.dataset import Dataset
from data_access.models import EqualsCondition
from dataset_selector.briefing import FileBriefingSource
from dataset_selector.capabilities import select_dataset
from dataset_selector.locator import LocalDatasetLocator
from dataset_selector.selector import StaticDatasetSelector
from dataset_selector.usage_log import JsonlSelectionLogger
from qa_agent.capabilities import _answer_with_selection
from qa_agent.deps import AgentDeps
from qa_agent.run_log import JsonlRunLogger
from qa_agent.settings import AgentSettings

REPO_ROOT = Path(__file__).parent.parent.parent.parent
BRIEFINGS_ROOT = REPO_ROOT / "data" / "briefings"
DATASETS_ROOT = REPO_ROOT / "data" / "datasets"
DATASET_KEY = "orcamentos-aeb-csv"
SOURCE_IDENTIFIER = "dados_gerais/tb_geral.csv"
AEB_UNIT_NAME = "Agência Espacial Brasileira"
QUESTION_YEAR = "2013"


def _real_selector() -> StaticDatasetSelector:
    return StaticDatasetSelector(
        briefing_source=FileBriefingSource(BRIEFINGS_ROOT),
        locator=LocalDatasetLocator(DATASETS_ROOT),
    )


def _real_aeb_2013_rows() -> list[dict[str, str | None]]:
    dataset = Dataset(DATASETS_ROOT / DATASET_KEY)
    result = real_query_rows(
        dataset,
        SOURCE_IDENTIFIER,
        [
            EqualsCondition(field="nome_unidade", value=AEB_UNIT_NAME),
            EqualsCondition(field="data_ano", value=QUESTION_YEAR),
        ],
    )
    return result.rows


def _answer(question: str, model, tmp_path: Path):
    selector = _real_selector()
    selection = select_dataset(
        question, selector=selector, logger=JsonlSelectionLogger(tmp_path / "selections.jsonl")
    )
    run_logger = JsonlRunLogger(tmp_path / "runs.jsonl")
    capture_deps: list[AgentDeps] = []
    result = _answer_with_selection(
        question,
        selection,
        run_logger=run_logger,
        settings=AgentSettings(model_name="test", instrument=False),
        model_override=model,
        capture_deps=capture_deps,
    )
    return result, capture_deps[0]


def test_as1_filter_then_aggregate_returns_correctly_computed_total(tmp_path: Path) -> None:
    expected_total = sum(float(row["pago"]) for row in _real_aeb_2013_rows() if row["pago"])

    call_count = {"n": 0}

    def scripted(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="query_rows",
                        args={
                            "identifier": SOURCE_IDENTIFIER,
                            "filters": [
                                {"field": "nome_unidade", "op": "equals", "value": AEB_UNIT_NAME},
                                {"field": "data_ano", "op": "equals", "value": QUESTION_YEAR},
                            ],
                        },
                    )
                ]
            )
        if call_count["n"] == 2:
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
            if g.group_values.get("nome_unidade") == AEB_UNIT_NAME
            and g.group_values.get("data_ano") == QUESTION_YEAR
        )
        value = matched.results["sum_pago"]
        answer = f"O total pago pela AEB em 2013 foi de R$ {value}."
        return ModelResponse(parts=[TextPart(json.dumps({"answer": answer, "outcome": "full"}))])

    result, deps = _answer(
        "Quanto foi pago pela AEB em 2013?", FunctionModel(scripted), tmp_path
    )

    assert result.outcome == "full"
    assert str(expected_total) in result.answer
    assert deps.step_budget.attempts >= 2


def test_as2_ranking_question_uses_full_data_not_a_partial_sample(tmp_path: Path) -> None:
    rows = _real_aeb_2013_rows()
    expected_best = max(rows, key=lambda r: float(r["pago"]) if r["pago"] else float("-inf"))
    expected_action = expected_best["nome_acao"]
    assert expected_action is not None

    def scripted(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if len(messages) == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="query_rows",
                        args={
                            "identifier": SOURCE_IDENTIFIER,
                            "filters": [
                                {"field": "nome_unidade", "op": "equals", "value": AEB_UNIT_NAME},
                                {"field": "data_ano", "op": "equals", "value": QUESTION_YEAR},
                            ],
                        },
                    )
                ]
            )
        last_request = messages[-1]
        tool_return = next(p for p in last_request.parts if isinstance(p, ToolReturnPart))
        best = max(
            tool_return.content.rows,
            key=lambda r: float(r["pago"]) if r["pago"] else float("-inf"),
        )
        answer = f"A ação com maior valor pago pela AEB em 2013 foi '{best['nome_acao']}'."
        return ModelResponse(parts=[TextPart(json.dumps({"answer": answer, "outcome": "full"}))])

    result, deps = _answer(
        "Qual ação teve o maior valor pago pela AEB em 2013?", FunctionModel(scripted), tmp_path
    )

    assert result.outcome == "full"
    assert expected_action in result.answer
    assert deps.step_budget.successes >= 1


def test_as3_inspects_schema_before_filtering_in_the_same_run(tmp_path: Path) -> None:
    call_order: list[str] = []
    call_count = {"n": 0}

    def scripted(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        call_count["n"] += 1
        if call_count["n"] == 1:
            call_order.append("inspect_schema")
            return ModelResponse(
                parts=[ToolCallPart(tool_name="inspect_schema", args={"identifier": SOURCE_IDENTIFIER})]
            )
        if call_count["n"] == 2:
            call_order.append("query_rows")
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="query_rows",
                        args={
                            "identifier": SOURCE_IDENTIFIER,
                            "filters": [
                                {"field": "nome_unidade", "op": "equals", "value": AEB_UNIT_NAME},
                            ],
                        },
                    )
                ]
            )
        return ModelResponse(
            parts=[TextPart(json.dumps({"answer": "Encontrei os registros da AEB.", "outcome": "full"}))]
        )

    result, deps = _answer(
        "Quais são os registros da AEB? Verifique antes os campos disponíveis.",
        FunctionModel(scripted),
        tmp_path,
    )

    assert result.outcome == "full"
    assert call_order == ["inspect_schema", "query_rows"]
    assert deps.step_budget.attempts >= 2
