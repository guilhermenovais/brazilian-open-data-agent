"""answer_question: the one public entry point of qa_agent (contracts/answering.md).

Never raises DatasetSelector*/DataAccessError/pydantic_ai exceptions to its caller —
every reachable failure is caught here and translated into a QuestionAnsweringResult
with a Portuguese answer and outcome="none" (research.md §10).
"""

from datetime import datetime, timezone
from typing import Literal, MutableSequence

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
from qa_agent.models import AgentAnswer, AgentRunLogEntry, QuestionAnsweringResult
from qa_agent.prompt_loader import render
from qa_agent.run_log import RunLogger
from qa_agent.settings import AgentSettings
from qa_agent.step_budget import RETRIEVAL_STEP_LIMIT, StepBudget

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
    except (NoBriefingsAvailableError, DatasetNotFoundError, BriefingNotFoundError):
        return _finalize(
            question=question,
            dataset_key=_UNKNOWN_DATASET_KEY,
            answer=_NO_DATASET_ANSWER,
            outcome="none",
            run_logger=run_logger,
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
    except Exception:
        return _finalize(
            question=question,
            dataset_key=selection.dataset_key,
            answer=_PROCESSING_FAILED_ANSWER,
            outcome="none",
            run_logger=run_logger,
        )

    agent_answer: AgentAnswer = run_result.output
    outcome = _clamp_outcome(reported=agent_answer.outcome, budget=step_budget)

    return _finalize(
        question=question,
        dataset_key=selection.dataset_key,
        answer=agent_answer.answer,
        outcome=outcome,
        run_logger=run_logger,
    )


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
) -> QuestionAnsweringResult:
    run_logger.log(
        AgentRunLogEntry(
            question=question,
            dataset_key=dataset_key,
            outcome=outcome,
            timestamp=datetime.now(timezone.utc),
        )
    )
    return QuestionAnsweringResult(answer=answer, dataset_key=dataset_key, outcome=outcome)
