# Quickstart: Validating the Question-Answering Agent Workflow

This is a runnable validation guide, not implementation code — it proves the feature works
end-to-end once built. See `data-model.md` for exact model shapes and `contracts/` for
behavior. Two tracks: a **deterministic track** (no API key, no network — proves the wiring)
and a **live-model track** (needs a real model configured — proves actual answer quality,
research.md §11).

## Prerequisites

- Python 3.11+, project virtualenv with `pydantic-ai`, `pydantic`, `pydantic-settings`,
  `pandas`, `pytest` installed.
- The real `data/briefings/orcamentos-aeb-csv.md` and `data/datasets/orcamentos-aeb-csv/`
  (used by both tracks).
- For the live-model track only: `QA_AGENT_MODEL` set to a real `pydantic-ai` model string
  (e.g. `QA_AGENT_MODEL=openai:gpt-4o-mini`) and that provider's own API key env var set
  (e.g. `OPENAI_API_KEY=...`).

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Deterministic track (CI-gated, no network)

### Scenario 1 — A grounded answer requires the tools to actually run (US1)

```python
from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart, TextPart

from qa_agent.agent_factory import build_agent
from qa_agent.settings import AgentSettings
from qa_agent.deps import AgentDeps
from qa_agent.step_budget import StepBudget
from dataset_selector.briefing import FileBriefingSource
from dataset_selector.locator import LocalDatasetLocator
from dataset_selector.selector import StaticDatasetSelector
from dataset_selector.capabilities import select_dataset
from dataset_selector.usage_log import JsonlSelectionLogger

selector = StaticDatasetSelector(
    briefing_source=FileBriefingSource("data/briefings"),
    locator=LocalDatasetLocator("data/datasets"),
)
selection = select_dataset(
    "Quanto foi pago pela AEB em 2015?",
    selector=selector,
    logger=JsonlSelectionLogger("data/logs/dataset_selections.jsonl"),
)

# A scripted model: calls aggregate_rows once, then answers — proves the wiring
# invokes the right tool and reports a "full" outcome when a fact is retrieved,
# with zero network calls.
def scripted(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    if len(messages) == 1:
        return ModelResponse(parts=[ToolCallPart(
            tool_name="aggregate_rows",
            args={
                "identifier": "dados_gerais/tb_geral.csv",
                "request": {
                    "group_by": ["nome_unidade", "data_ano"],
                    "aggregates": [{"value_field": "pago", "function": "sum"}],
                },
            },
        )])
    return ModelResponse(parts=[TextPart(
        '{"answer": "O valor pago pela AEB em 2015 foi de R$ ...", "outcome": "full"}'
    )])

agent = build_agent(AgentSettings(model_name="test", instrument=False))
deps = AgentDeps(dataset=selection.dataset, dataset_key=selection.dataset_key,
                  step_budget=StepBudget(limit=10))
result = agent.run_sync(
    "Quanto foi pago pela AEB em 2015?",
    deps=deps,
    model=FunctionModel(scripted),
)
assert deps.step_budget.successes == 1
assert result.output.outcome == "full"
```

**Expected outcome**: the tool wrapper actually executes `aggregate_rows` against the real
sample dataset (`deps.step_budget.successes == 1`), and the run reports `outcome="full"` —
proving the wiring path end-to-end without a real model call.

### Scenario 2 — Step budget cuts off at exactly 10 (FR-012)

```python
from qa_agent.step_budget import StepBudget

budget = StepBudget(limit=10)
for _ in range(10):
    assert budget.try_reserve() is True
assert budget.try_reserve() is False  # 11th attempt is refused, not executed
```

### Scenario 3 — Zero successful retrievals forces `outcome="none"` (research.md §5)

```python
from qa_agent.step_budget import StepBudget
from qa_agent.capabilities import _clamp_outcome  # or equivalent internal helper

budget = StepBudget(limit=10)
budget.try_reserve()  # one attempt, no record_success() — e.g. it raised ModelRetry
assert _clamp_outcome(reported="full", budget=budget) == "none"
```

**Expected outcome**: even if the model claims `"full"`, a request with zero successful
retrievals is always logged and returned as `"none"` — the anti-fabrication backstop.

### Scenario 4 — Dataset-selection failure never reaches the model (US4, Tier 1)

```python
from dataset_selector.briefing import FileBriefingSource
from dataset_selector.locator import LocalDatasetLocator
from dataset_selector.selector import StaticDatasetSelector
from dataset_selector.usage_log import JsonlSelectionLogger
from qa_agent.capabilities import answer_question
from qa_agent.run_log import JsonlRunLogger
from qa_agent.settings import AgentSettings

empty_selector = StaticDatasetSelector(
    briefing_source=FileBriefingSource("tests/fixtures/qa_agent/no_briefings"),
    locator=LocalDatasetLocator("data/datasets"),
)
result = answer_question(
    "Quanto foi pago pela AEB em 2015?",
    selector=empty_selector,
    selection_logger=JsonlSelectionLogger("data/logs/dataset_selections.jsonl"),
    run_logger=JsonlRunLogger("data/logs/qa_agent_runs.jsonl"),
    settings=AgentSettings(model_name="test", instrument=False),
)
assert result.outcome == "none"
assert "não" in result.answer.lower()  # a plain-language Portuguese refusal
```

### Scenario 5 — Every question is logged, even a failed one (FR-013)

```python
import json

log_path = "data/logs/qa_agent_runs.jsonl"
before = sum(1 for _ in open(log_path)) if __import__("os").path.exists(log_path) else 0

answer_question("Qualquer pergunta", selector=..., selection_logger=..., run_logger=JsonlRunLogger(log_path), settings=...)

lines = open(log_path).readlines()
assert len(lines) == before + 1
entry = json.loads(lines[-1])
assert {"question", "dataset_key", "outcome", "timestamp"} <= entry.keys()
```

## Live-model track (manual / opt-in, not part of the default CI gate)

Requires `QA_AGENT_MODEL` and a real provider API key. This is the evaluation harness
research.md §11 calls for — a fixed, versioned Portuguese question set checked against the
real sample dataset's actual values, run and recorded as a reproducible script (Constitution
Principle I), not a one-off manual check.

```bash
export QA_AGENT_MODEL=openai:gpt-4o-mini
export OPENAI_API_KEY=...  # provider-specific
python -m qa_agent.eval_harness  # implemented as a tasks.md follow-on; not part of pytest/CI
```

Representative questions to include (from spec.md's Independent Tests):

- "Quanto foi pago pela AEB em 2015?" (US1 — grounded single-fact answer)
- "Quanto foi gasto pela AEB em 2015?" (US1 AS2 — everyday synonym for "empenhado"/"pago")
- "Quanto o Ministério da Saúde gastou em 2015?" (US2 — out of coverage: wrong subject)
- "Qual ação teve o maior valor pago em 2015?" (US3 — filter + ranking)
- "Me fale sobre o orçamento." (Edge Case — too vague, treated as uncoverable)

**Expected outcome**: for each question, the harness records the model's answer alongside
the run's `AgentSettings` and a timestamp, and checks factual content against the dataset's
real values (SC-001/SC-002/SC-005) — a report a human then reviews, not a boolean CI gate.

## Running the deterministic suite

```bash
pytest tests/contract/qa_agent -v
pytest tests/unit/qa_agent -v
pyright src/
```

**Done when**: all contract tests (one per Acceptance Scenario in `spec.md`, driven by
`FunctionModel`/`TestModel`) pass with no network access, unit tests for `StepBudget`,
`prompt_loader`, and `JsonlRunLogger` pass in isolation, and `pyright` reports zero errors.
The live-model track is a documented follow-on (research.md §11), not required for this
command's own "done."
