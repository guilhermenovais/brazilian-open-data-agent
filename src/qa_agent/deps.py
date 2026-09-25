"""AgentDeps: RunContext[AgentDeps] dependency bundle, plain dataclass (Eng. Principle 4)."""

from dataclasses import dataclass, field

from data_access.dataset import Dataset
from data_access.text_matching import TextMatchingConfig
from qa_agent.step_budget import StepBudget


@dataclass
class AgentDeps:
    dataset: Dataset
    dataset_key: str
    step_budget: StepBudget
    text_matching: TextMatchingConfig = field(default_factory=TextMatchingConfig)
