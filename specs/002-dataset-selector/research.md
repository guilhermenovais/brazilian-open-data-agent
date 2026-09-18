# Phase 0 Research: Dataset Selector

## 1. Scope boundary: plain selection layer vs. pydantic-ai wiring

**Decision**: This feature implements only plain, framework-agnostic Python: the
`DatasetSelector`/`DatasetLocator`/`BriefingSource`/`SelectionLogger` abstractions, their
concrete implementations, and the one public capability function `select_dataset`. It does
**not** implement `@agent.tool` adapters or `RunContext[Deps]` wiring.

**Rationale**: Same as `001-data-access-tools` research.md §1 (Constitution Engineering
Principle 1). Nothing in this feature's spec mentions prompts, agent loops, or model
configuration — it's a lookup/selection capability the future wiring layer will call.

**Alternatives considered**: Building the `@agent.tool` wrapper now was rejected — no FR/SC
requires it, and it would conflate two independently testable layers.

## 2. The selection algorithm is a `Protocol`, defined now, because the spec itself names its future replacement

**Decision**: Define a `DatasetSelector` `Protocol` (`select(question: str) ->
DatasetSelectionResult`) with one implementation today, `StaticDatasetSelector`.

**Rationale**: Constitution Engineering Principle 2 requires defining an interface "before it
needs to vary" for axes *expected* to vary — and the spec's own Input section names the
replacement explicitly: "in the future, we will have thousands of datasets, and a complex
logic to select them (probably with subagents and RAG)." That is not a hypothetical the plan
is inventing; it is stated as a near-certain evolution. Defining the `Protocol` now means the
future, smarter selector is a new class written against this interface, never a rewrite of
`select_dataset`'s callers (FR-001/FR-002 stay stable — SC-004).

**Alternatives considered**: A bare function `select_dataset(question) -> ...` with no
`Protocol`, deferring the abstraction until a second implementation actually exists, was
considered (this is the codebase's own general bias against speculative abstraction,
Constitution VII). Rejected specifically here because — unlike a generic "maybe we'll need
this" guess — the spec text itself is the evidence (Constitution Principle II: evidence
before implementation) that a second implementation is coming and that today's behavior
(FR-003: always return the one dataset) must keep working unchanged once it arrives (SC-004).

## 3. `StaticDatasetSelector` never hardcodes the dataset's name

**Decision**: `StaticDatasetSelector` does not contain the string `"orcamentos-aeb-csv"`
anywhere. It asks its injected `BriefingSource` for `list_keys()` and always selects the
first key (sorted, for determinism). Today exactly one key exists, so that key is always
returned — satisfying FR-003 as an emergent property of "there is only one," not as a
hardcoded fact.

**Rationale**: Constitution Principle V: "The core system MUST NOT encode facts specific to
one dataset... in the general codebase." `orcamentos-aeb-csv` is a fact about today's data,
not about the selection mechanism. Keeping it out of `selector.py` means adding a second
dataset later (spec Edge Cases: "what happens when more than one briefing/dataset pair
exists") requires no code change to the selector itself to keep serving today's contract —
only a smarter `DatasetSelector` implementation is needed to *choose* between them, exactly
per §2.

**Alternatives considered**: Reading the key from a constant/config value (e.g.
`DATASET_KEY = "orcamentos-aeb-csv"`) was rejected — that constant would itself be exactly
the kind of dataset-specific fact Principle V forbids in the general codebase, and it
duplicates information the `data/briefings/` folder already encodes as a filename (FR-004).

## 4. Physical dataset location is resolved through a `DatasetLocator` `Protocol`, decoupled from selection

**Decision**: A `DatasetLocator` `Protocol` (`locate(key: str) -> Path`) with one
implementation today, `LocalDatasetLocator`, which maps a key to `<datasets_root>/<key>` and
raises `DatasetNotFoundError` if that folder doesn't exist (FR-005).

**Rationale**: The spec's Assumptions section states plainly that this will change: "Datasets
are currently stored locally in full... A future change will keep only briefings stored
locally and download full datasets on demand." That future `OnDemandDatasetLocator` (download
on cache miss, then return the local cache path) has the exact same signature as
`LocalDatasetLocator` — only its internals differ. Keeping this resolution step behind its own
`Protocol`, separate from `BriefingSource` and from `DatasetSelector`, means that future change
touches one new class, not the selection logic or the briefing lookup (Engineering Principle
2).

**Alternatives considered**: Folding location resolution into `DatasetSelector` itself was
rejected — it would force every future, smarter `DatasetSelector` (§2) to also know how to
fetch data files, conflating two independently-changing concerns (*which* dataset vs. *where*
its files physically live).

## 5. Briefing content is read through a `BriefingSource` `Protocol`

**Decision**: A `BriefingSource` `Protocol` (`list_keys() -> list[str]`, `get(key: str) ->
str`) with one implementation today, `FileBriefingSource`, backed by `.md` files under
`data/briefings/`. The key is the file's stem (name without `.md`), matching FR-004 exactly.

**Rationale**: The constitution names this exact abstraction by name as an Engineering
Principle 2 example: "a `BriefingSource` abstraction so manual and auto-generated briefings
are interchangeable." `list_keys()` is what lets `StaticDatasetSelector` (§3) avoid hardcoding
the dataset name, and is also the natural foundation a future RAG-based selector would use to
enumerate candidates to search over — so it is not added speculatively; both this feature's
own selector and the named future selector need it.

**Alternatives considered**: A single `get_default_briefing() -> str` method (skipping
`list_keys()`, since only one briefing exists today) was rejected — it would force
`StaticDatasetSelector` to either hardcode the key (§3) or reach past the `BriefingSource`
abstraction into the filesystem directly, defeating the point of the abstraction.

## 6. The result reuses the existing `Dataset` abstraction as-is for "location of data files"

**Decision**: `DatasetSelectionResult.dataset` is a `data_access.dataset.Dataset` instance —
the same class `001-data-access-tools` already established as "the sole owner of the
dataset's folder/identifier model" — constructed by `StaticDatasetSelector` from the path
`DatasetLocator.locate(key)` returns. The one adjustment needed: `DatasetSelectionResult` sets
`model_config = ConfigDict(arbitrary_types_allowed=True)`, since `Dataset` is a plain class,
not a pydantic model, and pydantic v2 rejects unknown arbitrary types by default.

**Rationale**: The spec's FR-002 requires the response to include "the location of the
dataset's data files." `Dataset` already *is* that: a fully-usable handle onto a dataset's
folder that the agent's existing tool layer (`discover_data_sources`, `inspect_schema`,
`query_rows`, `aggregate_rows` — all of `data_access.capabilities`) consumes directly.
Returning a bare `Path` instead would force every caller to immediately do
`Dataset(result.path)` themselves, duplicating a responsibility `Dataset` already owns (its
own docstring: "the sole owner of the dataset's folder/identifier model"). Reusing it directly
means a `DatasetSelectionResult` is immediately usable with the entire existing tool layer,
with no adapter step, and keeps the two features' contracts composable exactly as the spec's
own framing ("the agent... needs to know which dataset to consult and where to find it")
implies.

**Alternatives considered**: A bespoke `DatasetLocation` model (`root_path: str`) was
considered — rejected as an unjustified second location abstraction sitting next to `Dataset`,
which already exists and already does this job (Constitution VII: no unused generality).
Passing `Dataset` as a non-pydantic field without `arbitrary_types_allowed` was not viable —
pydantic v2 raises `PydanticSchemaGenerationError` for unrecognized types by default.

## 7. Usage logging is a `SelectionLogger` `Protocol`, minimal by design, not yet native tracing

**Decision**: A `SelectionLogger` `Protocol` (`log(entry: DatasetSelectionLogEntry) -> None`)
with one implementation, `JsonlSelectionLogger`, which appends one JSON line per decision to a
file. The public `select_dataset` capability function (not `StaticDatasetSelector` itself)
calls the logger exactly once per invocation, after the selector returns a result.

**Rationale**: FR-007/SC-005 require every selection decision to be recorded (Constitution
Principle X: "Usage as Research Data... is a first-class design concern"). Engineering
Principle 9 prefers pydantic-ai's native tracing over bespoke logging — but per §1, no
pydantic-ai wiring exists anywhere in this codebase yet, so native tracing isn't available to
lean on. `JsonlSelectionLogger` is deliberately the smallest thing that satisfies FR-007 today
(append-only, no query/rotation/retention logic) and is built as a swappable `Protocol`
implementation specifically so the future wiring layer can replace it with native
tracing-backed logging without touching `select_dataset`'s signature.

Logging lives in `select_dataset`, not inside `StaticDatasetSelector.select()`, so that every
current and future `DatasetSelector` implementation gets logging "for free" at the one call
site the spec's FR-001 actually describes ("a way for the agent to request the dataset"),
rather than needing to remember to log itself.

**Alternatives considered**: Using Python's stdlib `logging` module was considered and
rejected — FR-007/SC-005 require *structured, recorded* decisions (question, key, timestamp)
suitable for later research analysis, not free-text log lines; a small typed model + JSONL
appender is closer to Principle X's intent and is trivially parseable later. The module is
named `usage_log.py` (not `logging.py`) to avoid shadowing the stdlib module.

## 8. Key and error semantics

**Decision**: The key is exactly the briefing file's stem (`orcamentos-aeb-csv.md` →
`"orcamentos-aeb-csv"`), matched case-sensitively against a folder of the same name under
`data/datasets/`. Three typed exceptions: `DatasetNotFoundError` (locator: key's folder
missing — FR-005), `BriefingNotFoundError` (briefing source: `get()` called with a key that
has no `.md` file — defensive; unreachable through `select_dataset`'s own flow since it only
ever asks for keys `list_keys()` itself returned), `NoBriefingsAvailableError` (briefing
source has zero registered keys — nothing to select, an edge case the spec's Assumptions
section doesn't explicitly rule out but which FR-005's "surface a clear error, never
silently proceed" philosophy extends to naturally).

**Rationale**: Directly implements FR-004/FR-005. Errors are raised, not encoded in
`DatasetSelectionResult`, mirroring `001-data-access-tools` research.md §9's established
pattern in this codebase (keeps the success-path model clean; keeps `select_dataset` and the
`Protocol` implementations unit-testable without a model in the loop, Engineering Principle
6).

**Alternatives considered**: Letting a missing folder surface as an uncaught `FileNotFoundError`
was rejected — FR-005 explicitly requires "a clear error" over an incomplete/invalid result,
and an unqualified `FileNotFoundError` doesn't identify which dataset key or feature layer
failed.

## 9. Storage: usage log location

**Decision**: `JsonlSelectionLogger` takes an explicit `log_path` (no hidden default baked
into a global); the wiring/test code that constructs it will point it at
`data/logs/dataset_selections.jsonl`. `.gitignore` needs a `data/logs/` entry (it currently
ignores `*.log` but not `*.jsonl`) — tracked as an implementation task, not applied by this
planning step.

**Rationale**: Consistent with Engineering Principle 4 (DI over globals) and with how
`001-data-access-tools`'s `Dataset(root_path=...)` takes its root explicitly rather than
assuming a fixed location. Usage-log output is generated data, not source, so it shouldn't be
committed — same treatment as the `*.log` pattern already in `.gitignore`.

**Alternatives considered**: A fixed module-level constant path with no constructor
parameter was rejected — it would be a global, and would make `JsonlSelectionLogger`
untestable in isolation without writing into the real `data/` tree.

## 10. Type checker and test framework

**Decision**: `pyright` (CI) and `pytest`, unchanged from `001-data-access-tools` (research.md
§10–11) — same ecosystem, same codebase, no reason to diverge.

**Rationale**: Consistency; nothing in this feature's requirements motivates a different
choice.
