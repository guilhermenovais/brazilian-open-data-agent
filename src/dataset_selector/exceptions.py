"""Typed exceptions raised across the dataset selector capability boundary.

Raised rather than encoded into a success response model (research.md §8), mirroring
data_access.exceptions.DataAccessError's pattern.
"""


class DatasetSelectorError(Exception):
    """Base class for all dataset selector errors."""


class DatasetNotFoundError(DatasetSelectorError):
    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Dataset not found: {key!r}")


class BriefingNotFoundError(DatasetSelectorError):
    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Briefing not found: {key!r}")


class NoBriefingsAvailableError(DatasetSelectorError):
    def __init__(self) -> None:
        super().__init__("No briefings are available")
