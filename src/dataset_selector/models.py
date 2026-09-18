"""Pydantic I/O models crossing the dataset selector capability boundary.

Every tool input/output is a validated pydantic model (Constitution Engineering
Principle 5) — no untyped dicts cross this boundary.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from data_access.dataset import Dataset


class DatasetSelectionResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    dataset_key: str = Field(min_length=1)
    briefing: str
    dataset: Dataset


class DatasetSelectionLogEntry(BaseModel):
    question: str
    dataset_key: str
    timestamp: datetime
