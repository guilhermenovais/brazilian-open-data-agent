# Phase 0 Research: Question-Answering Agent Workflow

## 1. This feature is the `pydantic-ai` wiring layer — and stays thin anyway

**Decision**: `qa_agent` is the first package in this codebase to import `pydantic_ai`. It
builds one `Agent[AgentDeps, AgentAnswer]`, registers four tool wrappers over
`data_access.capabilities`, and exposes one public function, `answer_question`. All business
logic — dataset selection, discovery, schema inspection, filtered query, aggregation, locale
number parsing — is reused unmodified from `002-dataset-selector` and
`001-data-access-tools`. Nothing in either dependency module changes.

**Rationale**: `001`'s and `002`'s research.md §1 both explicitly deferred `@agent.tool`/
`RunContext[Deps]` wiring, citing Engineering Principle 1 ("orchestration... stays in a
small integration layer... All actual logic... lives in plain, framework-agnostic Python").
This plan is that integration layer arriving on schedule. Keeping it thin means: the only
files that import `pydantic_ai` are `tools.py` and `agent_factory.py`; everything else in
`qa_agent` (`step_budget.py`, `run_log.py`, `prompt_loader.py`, the outcome-clamp logic in
`capabilities.py`) is plain Python, unit-testable with no model or `pydantic-ai` object
involved at all.

**Alternatives considered**: Embedding tool-call logic directly inside `data_access`/
`dataset_selector` (e.g., decorating their functions with `@agent.tool` in place) was
rejected — it would force those two already-shipped, independently-tested packages to
depend on `pydantic-ai`, contradicting their own research.md §1 decisions and Engineering
Principle 1 generally.

## 2. Dataset selection is a deterministic pre-step, not a model-invoked tool

**Decision**: `answer_question` calls `dataset_selector.capabilities.select_dataset` exactly
once, before constructing or running the `Agent`. Its `DatasetSelectionResult` (dataset key,
briefing, `Dataset` handle) is used to (a) render the system prompt (§7) and (b) populate
`AgentDeps`. The model never sees dataset selection as a callable tool and cannot invoke it
more than once per question.

**Rationale**: FR-002 says the system "MUST determine which dataset applies to a question by
invoking the dataset selection capability *before* attempting any data retrieval" — a
sequencing requirement, not a delegation-to-the-model requirement. The spec's own Key
Entities section defines "Retrieval Step" as "one invocation of a data access capability
(discovery, schema inspection, filtered query, or aggregation)" — selection is explicitly
excluded from that definition, so it must not consume any of FR-012's 10-step budget, and
the cleanest way to guarantee that is to never expose it as an agent tool in the first place.
This is also Constitution Principle VI (deterministic computation over model judgment):
`002-dataset-selector` already made selection itself fully deterministic
(`StaticDatasetSelector` always returns the one registered key); there is no judgment call
here for a model to make today.

**Alternatives considered**: Exposing `select_dataset` as a first tool call the model must
make was rejected — it would (a) let a model call it zero, one, or many times with no
guarantee it happens "before any data retrieval" short of prompt-only enforcement, (b) force
an arbitrary decision about whether it counts against the 10-step budget, and (c) add
non-determinism to a step that `002` already made fully deterministic, for no benefit today.
If a future, smarter `DatasetSelector` (per `002`'s research.md §2) genuinely needs
per-question model judgment to choose among many datasets, that judgment belongs inside a
new `DatasetSelector` implementation (unchanged interface), not inside `qa_agent`.

## 3. The 10-step bound is enforced by a bespoke `StepBudget`, not a framework-generic limit

**Decision**: `AgentDeps` carries a `StepBudget` instance (`limit=10` fixed constant,
`attempts`, `successes` counters). Every one of the four tool wrappers increments `attempts`
before doing any work; if `attempts` would exceed 10, the wrapper does **not** call the
underlying `data_access` capability at all — it returns a small `BudgetExhausted` pydantic
model whose message tells the model, in Portuguese, that the step budget is exhausted and it
must produce its final answer now with whatever was already retrieved. On success, the
wrapper increments `successes`. Each tool's own `pydantic-ai` `retries` parameter is set to a
generous value (10) purely so the framework's own retry ceiling is never what terminates a
run — `StepBudget` is always the sole authority for FR-012.

**Rationale**: FR-012 defines the bound specifically in terms of "retrieval steps," which
the spec's Key Entities section scopes to exactly the four data-access capabilities (§2). A
generic `pydantic-ai` `UsageLimits(request_limit=...)` counts *model requests*, which would
also count the dataset-selection-adjacent overhead and the final structured-output-producing
request — not the same quantity the spec defines, and not precise enough to satisfy FR-012
exactly. A bespoke counter scoped to only the four retrieval tool wrappers is the only way to
match the spec's own definition precisely, and it is trivially unit-testable without any
model (`test_step_budget.py`), per Engineering Principle 6.

Returning a normal (non-exception) tool result on exhaustion, rather than raising, is
deliberate: it lets the model's own structured-output turn still run normally afterward, so
it can synthesize a genuine partial answer from whatever it already retrieved — exactly the
"partial facts" treatment the spec's clarification and FR-012 require, rather than crashing
the run and losing the chance to synthesize anything.

**Alternatives considered**: `pydantic-ai`'s built-in `UsageLimits(request_limit=N)` was
considered as the sole mechanism and rejected for the imprecision above, though it may still
be set generously (e.g. 30) as an unrelated, coarse safety net against pathological loops —
that is an operational nicety, not part of this feature's FR-012 contract, and is not
required for `tasks.md` to implement. Raising an exception on budget exhaustion (forcing an
immediate stop rather than letting the model finalize) was rejected — it would forfeit the
partial-answer requirement (FR-012, FR-007) for no benefit.

## 4. Tool-level failures become `ModelRetry`; only true dead-ends interrupt the loop

**Decision**: Each tool wrapper catches the `data_access.exceptions.DataAccessError` family
(`DataSourceNotFoundError`, `UnreadableSourceError`, `FieldNotFoundError`,
`NumericTypeError`, `IdentifierCollisionError`) and re-raises as `pydantic_ai.ModelRetry`
with a message describing what went wrong (e.g. "the field 'X' does not exist in source
'Y'"). This lets the model self-correct (e.g., re-inspect the schema and retry with a valid
field name) within the same step budget — each such attempt, whether it raises `ModelRetry`
or succeeds, still consumes one unit of the `StepBudget` from §3, so a model that keeps
guessing wrong field names still exhausts its 10 steps and is forced to finalize, never loops
unboundedly.

**Rationale**: `001-data-access-tools`'s research.md §9 explicitly named this exact
responsibility for "a future wiring layer": "Translating these exceptions into whatever
shape an agent-facing `@agent.tool` needs (e.g. a `ModelRetry`)... out of this feature's
scope." This is that future feature. `ModelRetry` is the idiomatic `pydantic-ai` mechanism
for "tool failed, but the model might recover by trying different arguments," which matches
FR-009's requirement to translate technical failures without ever exposing raw error text,
file paths, or identifiers *to the user* — the `ModelRetry` message is internal
model-context, not user-facing, so it is allowed to name the offending field/identifier (the
model needs that to self-correct); the final Portuguese answer the user sees is a separate,
later synthesis step, and the system prompt (§7) explicitly instructs the model never to
repeat internal identifiers there.

**Alternatives considered**: Swallowing `DataAccessError` and returning a generic "something
went wrong" tool result (no detail at all) was rejected — it would prevent the model from
distinguishing a recoverable mistake (wrong field name — re-inspect and retry) from a
fatal one (unreadable source — give up on that source), degrading User Story 3's multi-step
capability for no user-facing benefit, since none of this detail reaches the user anyway.

## 5. Outcome (full/partial/none) is model-judged, with one deterministic safety clamp

**Decision**: The `Agent`'s structured `output_type` is `AgentAnswer {answer: str, outcome:
Literal["full", "partial", "none"]}`. The model self-reports `outcome` as part of its final
turn. `answer_question` then applies one deterministic override: if `StepBudget.successes ==
0` (no retrieval ever actually succeeded during this request), `outcome` is forced to
`"none"` regardless of what the model reported, before it is logged or returned.

**Rationale**: Constitution Principle VI reserves model judgment for "genuine judgment calls
the system cannot resolve deterministically." Whether retrieved facts fully or only partially
answer a given natural-language question is exactly such a call — it requires understanding
the question's intent, which this codebase has no deterministic way to do (and isn't
building one; that would duplicate the model's own job). But "were zero facts ever
successfully retrieved" *is* mechanically knowable, and FR-005's anti-fabrication guarantee
must not depend solely on the model accurately self-reporting after the fact — a model that
hallucinated a "full" answer with zero real retrievals is exactly the failure mode FR-005
exists to prevent. The clamp is a deterministic backstop for that specific, checkable
failure mode, layered under (not replacing) the model's own judgment for the full/partial
distinction, which does require at least one real retrieval to even be plausible.

**Alternatives considered**: Trusting the model's self-reported `outcome` unconditionally was
rejected as leaving FR-005's core guarantee entirely to model reliability with no mechanical
check, for a case (zero retrievals) that costs nothing to verify deterministically. Having
the wiring layer compute full-vs-partial itself (e.g., some heuristic over retrieved row
counts) was rejected — no deterministic rule can know whether a given set of retrieved facts
actually answers an arbitrary Portuguese question; that determination is precisely what
requires the model.

## 6. Model provider configuration reuses `pydantic-ai`'s own model-string mechanism

**Decision**: `AgentSettings` (a `pydantic-settings` `BaseSettings`) has one required field,
`model_name: str` (env var `QA_AGENT_MODEL`, no default — a run must state its model
explicitly), passed as-is into `Agent(model=settings.model_name, ...)`. No bespoke
`ModelProvider` `Protocol` is introduced on top of it.

**Rationale**: The constitution's own Engineering Principle 2 example for this exact axis is
"a `ModelProvider`/model-config abstraction so OpenAI, OpenRouter, and local vLLM are all
'just configuration'" — but `pydantic-ai` already *is* that abstraction: its model string
syntax (`"openai:gpt-4o-mini"`, `"openrouter:..."`, etc.) plus explicit `Model` objects
(e.g. an OpenAI-compatible `OpenAIModel(..., base_url=...)` pointed at a local vLLM server)
already make provider choice "just configuration" with zero code change to swap. Building a
second, redundant abstraction on top would be exactly the "unused generality ahead of actual,
demonstrated need" Constitution Principle VII forbids. Requiring `model_name` with no
default (rather than silently defaulting to some provider) is what actually delivers
Engineering Principle 7's promise — "every experiment... must be expressible as an explicit,
recorded settings object" — a run's model is never implicit.

**Alternatives considered**: A hand-rolled `ModelProvider` `Protocol` wrapping `pydantic-ai`
models was considered and rejected per Constitution VII above. Hardcoding a specific default
model (e.g. always `"openai:gpt-4o-mini"`) was rejected — it would make model choice an
invisible fact baked into code rather than an explicit, recorded run configuration, working
against Reproducibility (Constitution I) the moment two runs with different models are ever
compared.

## 7. System prompt is a named, versioned template file with the briefing injected at render time

**Decision**: The Portuguese system prompt lives at `qa_agent/prompts/system_v1.md` — a
static template (fixed instructions: answer only in Portuguese, never fabricate, state which
field interpretation was used when ambiguous, translate failures into plain language, never
mention internal file/column/dataset names to the user) with one placeholder for the
selected dataset's briefing text. `prompt_loader.render(briefing: str) -> str` fills it in.
`agent_factory` calls it once per `answer_question` invocation (system prompts in
`pydantic-ai` can be dynamic per-run), using that question's actual selected briefing.

**Rationale**: Engineering Principle 8: "Prompt/briefing content is treated like a model
checkpoint: named, diffable, and referenced explicitly by the run configuration that used it
— never edited in place." A `system_v1.md` file (vs. an inline Python string) is trivially
diffable and versionable the same way `002`'s dataset briefings already are. Injecting the
briefing at render time (rather than duplicating its content into the template) is what
directly implements FR-003 ("use the selected dataset's briefing to interpret the
question... so the user is never required to know or name any technical schema detail").

**Alternatives considered**: An inline f-string built directly in `agent_factory.py` was
rejected — indistinguishable from "editing a prompt in place" with no independent diff/version
history, which Engineering Principle 8 specifically warns against.

## 8. Native instrumentation is finally switched on; the FR-013 run log stays separate

**Decision**: `AgentSettings.instrument: bool = True` is passed to `Agent(instrument=...)`,
enabling `pydantic-ai`'s built-in OpenTelemetry spans for model and tool calls. Wiring an
actual span *exporter* (Logfire, console, an OTel collector) is an operational/deployment
choice, out of this feature's scope — `instrument=True` alone makes the spans available to
whatever exporter configuration a deployment chooses, with no code change here. Separately,
`RunLogger`/`JsonlRunLogger` (mirroring `dataset_selector.usage_log`'s
`SelectionLogger`/`JsonlSelectionLogger` exactly) writes one `AgentRunLogEntry` — question,
`dataset_key`, final (clamped) `outcome`, timestamp — per question, called once by
`answer_question` after a final answer (positive, partial, or "cannot answer") is produced.

**Rationale**: `002-dataset-selector`'s research.md §7 documented a "deliberate gap": no
`pydantic-ai` wiring existed anywhere yet, so Engineering Principle 9 ("prefer native
instrumentation over bespoke logging") couldn't be satisfied for model/tool-call visibility,
only worked around with a minimal bespoke logger for its own narrower FR-007. This feature is
exactly the point where that gap closes for model/tool tracing generally. It does not,
however, make the bespoke run log redundant: FR-013 needs a specific, structured,
queryable-for-research record (one row per question, with exactly four fields) — a generic
tracing backend is the wrong tool for "list every question this dataset has answered and
whether it was ever fully answered," the same reasoning `002` already established for its own
selection log, now applied consistently to the run log.

**Alternatives considered**: Deriving FR-013's log purely from OTel spans after the fact
(e.g., a span-processing pipeline that reconstructs one row per question) was rejected as
premature infrastructure for a research-data need `JsonlRunLogger` already satisfies in five
lines, mirroring `002`'s own already-accepted pattern.

## 9. Run log shape and call site

**Decision**: `AgentRunLogEntry {question: str, dataset_key: str, outcome: Literal["full",
"partial", "none"], timestamp: datetime}`. `JsonlRunLogger(log_path)` appends one JSON line
per call, same shape as `JsonlSelectionLogger`. `answer_question` calls it exactly once,
after the (possibly clamped, §5) outcome is known — including on the dataset-selection-failure
and catastrophic-failure paths (§10), where `outcome="none"` and `dataset_key` is either the
key that failed to resolve (if selection got that far) or a sentinel value (if selection
itself never returned a key) — never left unlogged, since FR-013 requires a record "for each
question processed," with no carve-out for failed ones.

**Rationale**: Directly implements FR-013 and the spec's own Assumptions ("written once per
question, at the point a final answer... is produced... separate from... the dataset-selection
log entry already produced by the dataset selection module"). Logging failed/uncoverable
questions too (not just successes) is required by FR-013's literal wording and is itself
research-relevant — "how often does the agent fail to answer" is exactly the kind of usage
data Constitution Principle X cares about.

**Alternatives considered**: Only logging when an answer was fully or partially successful
(skipping "none" outcomes) was rejected as directly contradicting FR-013 and losing the
research signal a "none" outcome carries.

## 10. Failure translation map, and where the model loop is bypassed entirely

**Decision**: Three distinct failure tiers, each handled at a different layer:

1. **Dataset-selection failure** (`dataset_selector.exceptions.*`, e.g.
   `NoBriefingsAvailableError`, `DatasetNotFoundError`, `BriefingNotFoundError`) — caught by
   `answer_question` *before* any `Agent` is constructed. No model call happens at all; a
   fixed Portuguese "não foi possível determinar a base de dados para responder a esta
   pergunta" `AgentAnswer(outcome="none")` is returned directly and logged (§9, with a
   sentinel `dataset_key`).
2. **Retrieval-tool failure** (`data_access.exceptions.DataAccessError` family) — caught
   inside each tool wrapper, translated to `ModelRetry` (§4), consumed within the normal
   step budget; the model keeps running and still produces a real final answer.
3. **Catastrophic/model-call failure** (any exception escaping `agent.run()` itself — e.g.
   `pydantic_ai.exceptions.UnexpectedModelBehavior`, provider HTTP/network errors, or any
   other unexpected exception) — caught by `answer_question` around the `agent.run()` call.
   Because the model's own synthesis step never completed, no genuine partial answer can be
   salvaged from whatever was retrieved so far (there is no synthesis step to trust); a fixed
   Portuguese "não foi possível processar a pergunta no momento" `AgentAnswer(outcome="none")`
   is returned and logged.

**Rationale**: FR-009 requires *every* technical failure to become a plain Portuguese
explanation with zero raw error text/paths/identifiers surfaced to the user, and User Story
4 Acceptance Scenario 2 requires that a failure never be presented "as if it were complete
and correct." Tier 2 is the only tier where a genuine, trustworthy partial answer is even
possible, because it's the only tier where the model's own synthesis step still runs
afterward with real, grounded data in hand — tiers 1 and 3 have no such synthesis step to
rely on, so a fixed fallback message is the honest response, not an under-engineered one.

**Alternatives considered**: Attempting to synthesize a partial answer from whatever
retrievals happened before a Tier 3 crash (e.g., by inspecting `AgentDeps.step_budget`
outside the model loop and hand-assembling a message) was rejected — doing so without the
model's own language synthesis would mean qa_agent's plain wiring code is now responsible for
composing natural-language Portuguese content, which is exactly the model's job per this
feature's whole design, and duplicating it in wiring code for an already-rare failure path is
not justified by any FR.

## 11. Testing strategy: deterministic contract tests now, a separate evaluation harness for model quality

**Decision**: All `tests/contract/qa_agent/` tests use `pydantic_ai.models.function.FunctionModel`
(or `TestModel` where a scripted tool-call sequence isn't needed) to drive the `Agent`
deterministically — asserting the wiring behaves correctly (right tools called in the right
order, `ModelRetry` on injected failures, step budget enforced at exactly 10, outcome clamp
applied, run log written) without any network call or API key, exactly mirroring how `001`
and `002`'s contract tests need no model at all. Separately, this plan calls out — but does
not implement as part of `tasks.md`'s CI-gated suite — a live-model evaluation harness: a
fixed, versioned set of Portuguese test questions (the ones spec.md's Independent Tests
already name, e.g. "quanto foi pago pela AEB em 2015?") run against a real configured model,
with expected values checked against the actual `data/datasets/orcamentos-aeb-csv` data, and
the full run configuration (`AgentSettings`, question set, model, timestamp) recorded
alongside the results.

**Rationale**: SC-001, SC-002, and SC-005 are claims about *model* behavior (factual accuracy,
refusal correctness, multi-step success rate) that no scripted double can validate — a
`FunctionModel` test only proves the wiring behaves correctly *given* whatever the model
decides to do, never that a real model actually decides correctly. Constitution Principle I
forbids presenting "a manually-run, hand-graded, one-time report" as a finding — so this
harness must itself be a reusable, re-runnable script (not an ad hoc manual check), even
though it needs live credentials and network access unavailable in this environment's
default CI run. This plan documents that harness's existence and shape (as `tasks.md`
follow-on work) rather than skipping it silently, satisfying Principle II (evidence before
implementation) for whatever future claim is made about the finished feature's real-world
accuracy.

**Alternatives considered**: Asserting SC-001/002/005 via `FunctionModel`-scripted "the model
always produces X" tests was rejected — it would test the wiring's reaction to a scripted
answer, not whether a real model actually produces a grounded one, giving false confidence
that these Success Criteria are met.

## 12. Type checker and test framework

**Decision**: `pyright` (CI) and `pytest`, unchanged from `001`/`002` (their research.md
§10/§11). `pydantic-ai`'s own type stubs are typed throughout, so `Agent[AgentDeps,
AgentAnswer]`'s generics are checked the same way `QueryEngine`/`DataSourceReader` `Protocol`s
already are.

**Rationale**: Consistency; nothing in this feature's requirements motivates a different
choice.
