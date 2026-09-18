"""AgentDeps: RunContext[AgentDeps] dependency bundle, plain dataclass (Eng. Principle 4)."""

from dataclasses import dataclass

from data_access.dataset import Dataset
from qa_agent.step_budget import StepBudget


@dataclass
class AgentDeps:
    dataset: Dataset
    dataset_key: str
    step_budget: StepBudget
