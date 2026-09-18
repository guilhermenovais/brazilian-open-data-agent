"""The public capability entry point of the dataset selector tool layer.

Plain Python function (Constitution Engineering Principle 1 — no `pydantic-ai`
import). A future `@agent.tool` adapter wraps this 1:1.
"""

from datetime import datetime, timezone

from dataset_selector.models import DatasetSelectionLogEntry, DatasetSelectionResult
from dataset_selector.selector import DatasetSelector
from dataset_selector.usage_log import SelectionLogger


def select_dataset(
    question: str,
    selector: DatasetSelector,
    logger: SelectionLogger,
) -> DatasetSelectionResult:
    result = selector.select(question)
    logger.log(
        DatasetSelectionLogEntry(
            question=question,
            dataset_key=result.dataset_key,
            timestamp=datetime.now(timezone.utc),
        )
    )
    return result
