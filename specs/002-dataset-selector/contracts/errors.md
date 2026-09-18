# Contract: Errors

All exceptions subclass `DatasetSelectorError` (base class, mirrors
`data_access.exceptions.DataAccessError`). Raised, never encoded into a success-path model
(research.md §8).

| Exception                  | Raised by | Condition | Carries |
|-----------------------------|-----------|-----------|---------|
| `DatasetNotFoundError`      | `LocalDatasetLocator.locate` | The key has no matching folder under the datasets directory (FR-005). | `key: str` |
| `BriefingNotFoundError`     | `FileBriefingSource.get` | Called directly with a key that has no `.md` file. Defensive — not reachable through `select_dataset`'s own flow, since `StaticDatasetSelector` only ever passes keys it just got from `list_keys()` on the same source. | `key: str` |
| `NoBriefingsAvailableError` | `StaticDatasetSelector.select` | `BriefingSource.list_keys()` returned an empty list — nothing is registered to select. | — |
