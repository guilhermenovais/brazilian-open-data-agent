# Shared Error Types

All four capabilities (discovery, inspection, query, aggregation) raise from this shared set
of typed exceptions rather than encoding failure into the success response models
(research.md §9). A future `@agent.tool` wiring layer (out of scope for this feature,
research.md §1) is responsible for catching these and translating them into whatever an
agent-facing tool response needs.

| Exception | `__init__` fields | FR |
|-----------|--------------------|----|
| `DataSourceNotFoundError` | `identifier: str` | FR-012 |
| `UnreadableSourceError` | `identifier: str`, `detail: str` | FR-001a |
| `FieldNotFoundError` | `identifier: str`, `field: str` | FR-012 |
| `NumericTypeError` | `identifier: str`, `field: str` | FR-013 |
| `IdentifierCollisionError` | `identifier: str`, `physical_paths: list[str]` | FR-012a |

All five derive from a common `DataAccessError(Exception)` base so a caller can catch any
tool-layer failure with one `except` clause when it doesn't need to distinguish the cause.

Every exception's `str()` MUST be a clear, human/model-readable message naming the offending
identifier/field so it can be surfaced directly to the agent without extra formatting
(SC-005: zero silent empty/fabricated results).
