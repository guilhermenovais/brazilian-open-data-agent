"""answer_question: the one public entry point of qa_agent (contracts/answering.md).

Never raises DatasetSelector*/DataAccessError/pydantic_ai exceptions to its caller —
every reachable failure is caught here and translated into a QuestionAnsweringResult
with a Portuguese answer and outcome="none" (research.md §10).

The caught exception is no longer discarded: it is described as a `FailureDetail`
(root-cause type, redacted and length-capped message, transient verdict) and carried on
both the returned result and the run log entry (006 contracts/failure-details.md). The
Portuguese answer texts themselves are unchanged.
"""

from datetime import datetime, timezone
from typing import Literal, MutableSequence

from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage, ToolCallPart, ToolReturnPart
from pydantic_ai.models import Model

from dataset_selector.capabilities import select_dataset
from dataset_selector.exceptions import (
    BriefingNotFoundError,
    DatasetNotFoundError,
    NoBriefingsAvailableError,
)
from dataset_selector.models import DatasetSelectionResult
from dataset_selector.selector import DatasetSelector
from dataset_selector.usage_log import SelectionLogger

from qa_agent.agent_factory import build_agent
from qa_agent.deps import AgentDeps
from qa_agent.failures import describe_failure, never_transient
from qa_agent.models import (
    AgentAnswer,
    AgentRunLogEntry,
    FailureDetail,
    QuestionAnsweringResult,
    RetrievalStep,
)
from qa_agent.prompt_loader import render
from qa_agent.run_log import RunLogger
from qa_agent.settings import AgentSettings
from qa_agent.step_budget import RETRIEVAL_STEP_LIMIT, StepBudget
from qa_agent.transient import classify

_NO_DATASET_ANSWER = "Não foi possível determinar a base de dados para responder a esta pergunta."
_PROCESSING_FAILED_ANSWER = "Não foi possível processar a pergunta no momento."
_UNKNOWN_DATASET_KEY = "<none>"


def answer_question(
    question: str,
    *,
    selector: DatasetSelector,
    selection_logger: SelectionLogger,
    run_logger: RunLogger,
    settings: AgentSettings,
) -> QuestionAnsweringResult:
    try:
        selection = select_dataset(question, selector, selection_logger)
    except (NoBriefingsAvailableError, DatasetNotFoundError, BriefingNotFoundError) as exc:
        return _finalize(
            question=question,
            dataset_key=_UNKNOWN_DATASET_KEY,
            answer=_NO_DATASET_ANSWER,
            outcome="none",
            run_logger=run_logger,
            errored=True,
            failure=describe_failure(exc, secrets=[settings.api_key], classify=never_transient),
        )

    return _answer_with_selection(question, selection, run_logger=run_logger, settings=settings)


def _answer_with_selection(
    question: str,
    selection: DatasetSelectionResult,
    *,
    run_logger: RunLogger,
    settings: AgentSettings,
    model_override: Model | str | None = None,
    capture_deps: MutableSequence[AgentDeps] | None = None,
) -> QuestionAnsweringResult:
    """Runs the agent for an already-resolved dataset selection and logs the result.

    Split out of `answer_question` so contract tests can inject a scripted
    `pydantic_ai` test-double model (`model_override`) without a live model call —
    `AgentSettings.model_name` is a plain `str` (Engineering Principle 7) and cannot
    itself carry a test double, and `pydantic-ai`'s own model-override mechanism is
    scoped to a specific `Agent` instance, which `answer_question` never exposes.
    `capture_deps`, if given, has the run's `AgentDeps` appended to it so a test can
    inspect `step_budget` after the call — another test-only seam for the same reason.
    """
    step_budget = StepBudget(limit=RETRIEVAL_STEP_LIMIT)
    deps = AgentDeps(
        dataset=selection.dataset,
        dataset_key=selection.dataset_key,
        step_budget=step_budget,
    )
    if capture_deps is not None:
        capture_deps.append(deps)
    agent = build_agent(settings)
    system_prompt = render(selection.briefing)

    try:
        run_result = agent.run_sync(
            question, deps=deps, instructions=system_prompt, model=model_override
        )
    except Exception as exc:
        return _finalize(
            question=question,
            dataset_key=selection.dataset_key,
            answer=_PROCESSING_FAILED_ANSWER,
            outcome="none",
            run_logger=run_logger,
            errored=True,
            failure=describe_failure(exc, secrets=[settings.api_key], classify=classify),
        )

    agent_answer: AgentAnswer = run_result.output
    outcome = _clamp_outcome(reported=agent_answer.outcome, budget=step_budget)
    steps = _extract_steps(run_result.all_messages())

    return _finalize(
        question=question,
        dataset_key=selection.dataset_key,
        answer=agent_answer.answer,
        outcome=outcome,
        run_logger=run_logger,
        steps=steps,
    )


def _extract_steps(messages: list[ModelMessage]) -> list[RetrievalStep]:
    steps: list[RetrievalStep] = []
    calls_by_id: dict[str, ToolCallPart] = {}
    for message in messages:
        for part in message.parts:
            if isinstance(part, ToolCallPart):
                calls_by_id[part.tool_call_id] = part
            elif isinstance(part, ToolReturnPart):
                call = calls_by_id.get(part.tool_call_id)
                if call is None:
                    continue
                arguments = call.args_as_dict() if isinstance(call.args, str) else dict(call.args or {})
                content = part.content
                if isinstance(content, BaseModel):
                    result_summary = content.model_dump_json()
                else:
                    result_summary = str(content)
                steps.append(
                    RetrievalStep(
                        tool_name=call.tool_name,
                        arguments=arguments,
                        result_summary=result_summary,
                    )
                )
    return steps


def _clamp_outcome(
    *, reported: Literal["full", "partial", "none"], budget: StepBudget
) -> Literal["full", "partial", "none"]:
    if budget.successes == 0:
        return "none"
    return reported


def _finalize(
    *,
    question: str,
    dataset_key: str,
    answer: str,
    outcome: Literal["full", "partial", "none"],
    run_logger: RunLogger,
    steps: list[RetrievalStep] | None = None,
    errored: bool = False,
    failure: FailureDetail | None = None,
) -> QuestionAnsweringResult:
    run_logger.log(
        AgentRunLogEntry(
            question=question,
            dataset_key=dataset_key,
            outcome=outcome,
            timestamp=datetime.now(timezone.utc),
            failure=failure,
        )
    )
    return QuestionAnsweringResult(
        answer=answer,
        dataset_key=dataset_key,
        outcome=outcome,
        steps=steps or [],
        errored=errored,
        failure=failure,
    )
