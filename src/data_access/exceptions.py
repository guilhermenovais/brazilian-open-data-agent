"""Typed exceptions raised across the data access tool layer's capability boundary.

Capabilities raise these rather than encoding failure into success response models
(research.md §9), so a future wiring layer can catch and translate them without the
capability functions needing to know how an agent surfaces errors.
"""


class DataAccessError(Exception):
    """Base class for all data access tool layer errors."""


class DataSourceNotFoundError(DataAccessError):
    def __init__(self, identifier: str) -> None:
        self.identifier = identifier
        super().__init__(f"Data source not found: {identifier!r}")


class UnreadableSourceError(DataAccessError):
    def __init__(self, identifier: str, detail: str) -> None:
        self.identifier = identifier
        self.detail = detail
        super().__init__(f"Data source {identifier!r} could not be read: {detail}")


class FieldNotFoundError(DataAccessError):
    def __init__(self, identifier: str, field: str) -> None:
        self.identifier = identifier
        self.field = field
        super().__init__(f"Field {field!r} not found in data source {identifier!r}")


class NumericTypeError(DataAccessError):
    def __init__(self, identifier: str, field: str) -> None:
        self.identifier = identifier
        self.field = field
        super().__init__(
            f"Field {field!r} in data source {identifier!r} is not numeric-like"
        )


class InvalidSortKeyError(DataAccessError):
    def __init__(self, identifier: str, key: str, valid_keys: list[str]) -> None:
        self.identifier = identifier
        self.key = key
        self.valid_keys = valid_keys
        super().__init__(
            f"Sort key {key!r} is not valid for data source {identifier!r}; "
            f"valid keys: {valid_keys!r}"
        )


class IdentifierCollisionError(DataAccessError):
    def __init__(self, identifier: str, physical_paths: list[str]) -> None:
        self.identifier = identifier
        self.physical_paths = physical_paths
        super().__init__(
            f"Identifier {identifier!r} is ambiguous: resolves to multiple physical "
            f"paths: {physical_paths}"
        )
