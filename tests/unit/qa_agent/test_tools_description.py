"""The registered `aggregate_rows` tool documents the 007 request fields (FR-017;
specs/007-aggregate-rows-enhancements/contracts/aggregate-rows-tool.md), and the data
tools state the 009 text-matching behavior (FR-018;
specs/009-text-value-matching/contracts/agent-tools-and-runs.md)."""

import json

from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.tools import ToolDefinition

from data_access.dataset import Dataset
from qa_agent.agent_factory import build_agent
from qa_agent.deps import AgentDeps
from qa_agent.settings import AgentSettings
from qa_agent.step_budget import StepBudget

FUNCTIONS = ["count", "sum", "mean", "min", "max", "count_distinct"]


def _aggregate_rows_tool(tmp_path) -> ToolDefinition:
    return _tools(tmp_path)["aggregate_rows"]


def _tools(tmp_path) -> dict[str, ToolDefinition]:
    captured: dict[str, ToolDefinition] = {}

    def model_fn(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        for tool in info.function_tools:
            captured[tool.name] = tool
        (output_tool,) = info.output_tools
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name=output_tool.name,
                    args=json.dumps({"answer": "ok", "outcome": "none"}),
                )
            ]
        )

    agent = build_agent(AgentSettings(model_name="test", instrument=False))
    deps = AgentDeps(dataset=Dataset(tmp_path), dataset_key="test", step_budget=StepBudget(1))
    agent.run_sync("q", deps=deps, model=FunctionModel(model_fn))
    return captured


def test_description_documents_filters_functions_keys_order_and_limit(tmp_path) -> None:
    description = _aggregate_rows_tool(tmp_path).description or ""
    assert "before grouping" in description
    for function in FUNCTIONS:
        assert function in description
    assert "<function>_<value_field>" in description
    assert "sum_valor" in description
    for word in ("order_by", "desc", "limit", "total_group_count", "truncated"):
        assert word in description


def test_request_schema_includes_new_fields_and_function_enum(tmp_path) -> None:
    schema = _aggregate_rows_tool(tmp_path).parameters_json_schema
    text = json.dumps(schema)
    for field in ("filters", "order_by", "limit"):
        assert f'"{field}"' in text
    defs = schema.get("$defs", {})
    enums = [
        prop.get("enum")
        for model in defs.values()
        for prop in model.get("properties", {}).values()
    ]
    assert FUNCTIONS in enums


# --- 009 FR-018 ------------------------------------------------------------------------


def _assert_states_filter_and_suggestion_facts(description: str) -> None:
    text = " ".join(description.lower().split())
    for fact in ("case", "accents", "punctuation", "whole value", "value_suggestions"):
        assert fact in text, fact
    assert "every word" in text
    assert '"de"' in text and '"do"' in text
    assert "any order" in text
    assert "0 rows" in text or "no rows" in text


def test_009_query_rows_description_states_matching_and_suggestions(tmp_path) -> None:
    _assert_states_filter_and_suggestion_facts(_tools(tmp_path)["query_rows"].description or "")


def test_009_aggregate_rows_description_states_matching_and_suggestions(tmp_path) -> None:
    _assert_states_filter_and_suggestion_facts(
        _tools(tmp_path)["aggregate_rows"].description or ""
    )


def test_009_inspect_schema_description_states_value_lists(tmp_path) -> None:
    description = _tools(tmp_path)["inspect_schema"].description or ""
    for word in ("distinct_count", "values", "value_list_threshold", "filters"):
        assert word in description, word


def test_009_equals_and_contains_value_schemas_have_descriptions(tmp_path) -> None:
    defs = _tools(tmp_path)["query_rows"].parameters_json_schema.get("$defs", {})
    for model in ("EqualsCondition", "ContainsCondition"):
        description = defs[model]["properties"]["value"].get("description", "")
        assert "accents" in description, model
