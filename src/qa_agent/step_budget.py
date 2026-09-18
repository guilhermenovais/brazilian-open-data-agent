"""StepBudget: the 10-retrieval-step bound (FR-012).

Plain Python, not pydantic — it never crosses the tool boundary to the model, it's
pure in-process orchestration state (data-model.md).
"""

from pydantic import BaseModel

RETRIEVAL_STEP_LIMIT = 10


class StepBudget:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.attempts = 0
        self.successes = 0

    def try_reserve(self) -> bool:
        if self.attempts < self.limit:
            self.attempts += 1
            return True
        return False

    def record_success(self) -> None:
        self.successes += 1


class BudgetExhausted(BaseModel):
    message: str = (
        "O limite de etapas de consulta aos dados foi atingido. Finalize sua resposta "
        "agora com base apenas no que já foi obtido até aqui."
    )
