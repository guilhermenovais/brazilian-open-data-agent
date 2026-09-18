# Phase 0 Research: Testset Runner for LLM Evaluation

## 1. A new sibling package, thin wiring, reusing `qa_agent.answer_question` unmodified in spirit

**Decision**: `testset_runner` is a new package alongside `data_access`, `dataset_selector`, and
`qa_agent`. It never talks to `pydantic-ai`, a `Dataset`, or a briefing directly — for every
question it calls `qa_agent.capabilities.answer_question` (extended per §3/§4 below) exactly
once, through a small `QuestionAnswerer` `Protocol` seam. All new business logic —
testset loading/validation, match determination, run persistence, run comparison — is plain,
framework-agnostic Python.

**Rationale**: Engineering Principle 1 ("orchestration is a thin wiring layer... all actual
logic lives in plain, framework-agnostic Python"). `qa_agent` already *is* "ask one isolated
question against a configured model and get a structured result" (`003`'s own contract); this
feature's job is running that capability many times over a fixed question set, grading the
results, and persisting/comparing runs — none of which requires a second, parallel path into
`pydantic-ai`. Duplicating agent-construction logic inside `testset_runner` would violate
Principle V (separate mechanism from domain knowledge: dataset/model wiring is `qa_agent`'s
concern, not this feature's) and create two places that could drift on how a question is
actually answered.

**Alternatives considered**: Building `testset_runner` directly on top of `qa_agent.agent_factory`
and `dataset_selector` (bypassing `answer_question`) was rejected — it would reproduce the
Tier 1/2/3 failure-translation and outcome-clamping logic `003`'s research.md §5/§10 already
solved, for no benefit, and would let `testset_runner` silently diverge from how a real
question-answering caller behaves, undermining SC-006 (a run's structure must stay stable and
representative over time).

## 2. Per-question isolation is inherited for free — no new mechanism needed

**Decision**: `testset_runner.runner.run_testset` loops over a `Testset`'s questions strictly
sequentially, calling `answerer.answer(question.text)` (the `QuestionAnswerer` seam over
`answer_question`) once per question, and stores each returned result immediately into that
question's own `QuestionResult`. No object is shared or mutated across two questions' calls.

**Rationale**: FR-003 and SC-004 require zero cross-question leakage. `003`'s own design
already guarantees this at the `answer_question` level: every call builds a fresh
`AgentDeps`/`StepBudget`/`Agent` (Engineering Principle 4 — no module-level global agent
instance) and the model's own conversation history is never carried between `agent.run_sync`
calls. `testset_runner` only needs to *not undo* that guarantee — i.e., never pass one
question's `AgentDeps`, dataset selection, or model conversation into the next — which the
simple "call once per question, keep nothing but the returned result" loop shape trivially
satisfies. No new isolation mechanism (no explicit "reset state" step) is needed or introduced.

**Alternatives considered**: An explicit per-question "fresh context" object threaded through
`testset_runner`'s loop was considered and rejected as redundant ceremony — there is no shared
mutable state in the loop to reset in the first place once `answer_question` itself is trusted
as the isolation boundary.

## 3. Retrieval-step visibility requires two additive fields on `qa_agent`'s public contract

**Decision**: `qa_agent.models.QuestionAnsweringResult` gains two new fields:
`steps: list[RetrievalStep]` and `errored: bool = False`. `RetrievalStep {tool_name: str,
arguments: dict, result_summary: str}` is a new pydantic model, populated inside
`qa_agent.capabilities._answer_with_selection` by walking `run_result.all_messages()` for
`ToolCallPart`/`ToolReturnPart` pairs after a successful `agent.run_sync` call. `errored` is
set `True` in the two existing `except` branches of `capabilities.py` (dataset-selection
failure and catastrophic model-call failure) and left `False` on every path that reaches a real
`AgentAnswer`. Both fields default to values that make them backward compatible with `003`'s
existing contract tests (`errored` defaults `False`; `steps` defaults to `[]` and is simply
unpopulated on the two failure paths, where there is nothing to report anyway).

**Rationale**: FR-005 requires the run report to show, per question, "the sequence of retrieval
steps/tool actions the agent took" — data that already exists transiently inside
`pydantic-ai`'s message history for every `agent.run_sync` call but that `answer_question`
today discards after computing its outcome. Engineering Principle 2 ("define an interface
before the second implementation... trying a new approach must mean writing a new class
against an existing interface, never editing callers") applies here in its literal sense:
`testset_runner` is the second real consumer of `answer_question`'s internals, and its actual
need — the tool-call trace and a genuine errored/not-errored signal distinct from a legitimate
`outcome="none"` — is exactly the trigger the principle names for finally exposing it, rather
than reaching past the public contract or re-deriving it by string-matching `003`'s two fixed
fallback answer strings (which would silently break if those strings ever changed wording).
Exposing `errored` is what lets `testset_runner` tell "the agent looked and genuinely found
nothing" (`outcome="none"`, `errored=False` — a legitimate not-matched/needs-review case) apart
from "something broke before an answer was even attempted" (`errored=True` — a distinct
`match_status="errored"` per the spec's Key Entities), which the current contract cannot
distinguish at all.

**Alternatives considered**: Reconstructing the step trace from `AgentRunLogEntry`/tracing spans
after the fact was rejected — `003`'s research.md §8 explicitly scoped the run log to four
fixed fields and native tracing to an external, unconfigured OTel exporter; neither is a
structured, in-process return value `testset_runner` can consume synchronously. String-matching
`answer_question`'s two fixed fallback messages to infer `errored` was rejected as exactly the
kind of fragile, implicit cross-package coupling Principle V's "never encode facts specific to
one... deployment" warns against — an explicit boolean is one line to set and cannot drift out
of sync with the message text.

## 4. Target Configuration (model + URL) extends `AgentSettings`, using `pydantic-ai`'s own provider construction

**Decision**: `qa_agent.settings.AgentSettings` gains two optional fields: `base_url: str |
None = None` (env `QA_AGENT_BASE_URL`) and `api_key: str | None = None` (env
`QA_AGENT_API_KEY`). `qa_agent.agent_factory.build_agent` is changed to accept a settings
object as today, but when `base_url` is set it builds `Agent(model=OpenAIChatModel(model_name,
provider=OpenAIProvider(base_url=base_url, api_key=api_key)))` instead of passing
`model_name` straight through as a bare string; when `base_url` is unset, behavior is
byte-for-byte identical to `003` today (`Agent(model=settings.model_name)`). `testset_runner`
builds one `AgentSettings` per run from its own `TargetConfiguration` (itself built from CLI
flags — §9) and passes it straight through to `answer_question`, unchanged from how `003`
already threads settings today.

**Rationale**: FR-002/US3 require picking "which model and which URL/endpoint" per run
"without editing source code... or wiring up new environment variables by hand each time."
`003`'s research.md §6 deliberately deferred a `ModelProvider` abstraction, reasoning that
"`pydantic-ai` already *is* that abstraction" via model strings and "explicit `Model` objects
(e.g. an OpenAI-compatible `OpenAIModel(..., base_url=...)`" — this feature is precisely the
"actual, demonstrated need" `003` said would justify exercising that path, per Constitution
Principle VII (no unused generality *ahead of* demonstrated need — the need has now arrived).
Extending `AgentSettings` (rather than inventing a parallel `TestsetRunner`-only settings type
for the model) keeps exactly one typed settings object governing how any `qa_agent.Agent` gets
built, so a testset run's target configuration and a plain `answer_question` call's target
configuration are always expressed the same way (Engineering Principle 7 — "every experiment...
expressible as an explicit, recorded settings object").

**Alternatives considered**: A bespoke `ModelProvider` `Protocol` with per-provider subclasses
(`OpenAIModelProvider`, `VllmModelProvider`, ...) was rejected — `pydantic-ai`'s own
`Provider`/`Model` classes already fill that role; wrapping them in a second, project-specific
hierarchy would be the exact "unused generality" Principle VII forbids, since `base_url` plus
the existing model-string mechanism already covers every case FR-002/US3 describe (a
different hosted provider, a self-hosted OpenAI-compatible endpoint such as local vLLM). A
`testset_runner`-local settings object that reimplements `AgentSettings` was rejected as
duplicating Engineering Principle 7's "one typed settings object" per axis of variation, for
no benefit.

## 5. Match determination: a `MatchStrategy` interface with one concrete numeric strategy today

**Decision**: `testset_runner.matcher` defines a `MatchStrategy` `Protocol`
(`evaluate(expected: str, actual_answer: str) -> Literal["matched", "not_matched",
"needs_review"]`) and one concrete implementation, `NumericMatchStrategy`, wired as the sole
strategy inside a `DeterministicMatcher`. For a question whose `expected` value parses as a
number — reusing `data_access.numeric.parse_locale_number` unmodified, after stripping an
optional leading `~` (marking an approximate/tolerant expectation) — `NumericMatchStrategy`
scans the agent's free-text `actual_answer` for numeric-looking substrings, parses each with
the same `parse_locale_number`, and reports `matched` if any parsed value equals the expected
value (exact equality when there was no `~`; within a small relative tolerance when there was).
Any question whose `expected` value does **not** parse as a number — a bare name, a
composite "/"-joined multi-field fact, or descriptive text like "Data not available..." — is
always `needs_review`, regardless of its length or apparent simplicity.

**Rationale**: FR-006/FR-007 draw the auto-grade/human-review line exactly at "directly
comparable value (e.g., a number)" vs. everything else, and the spec's Assumptions permit but
do not require auto-grading "short exact strings." Constitution Principle VI (deterministic
computation over model judgment) demands that whatever *is* auto-graded be genuinely
mechanical, not a heuristic dressed up as one. A substring-containment check against an
LLM-generated prose answer is not that: a composite fact like `"Agência Espacial Brasileira /
Apoio Administrativo / 238959"` (this feature's own bundled testset, question 46) would almost
never appear in that literal joined form inside a natural-language sentence even when the
agent's answer is substantively correct, and a coincidental partial match could just as easily
produce a false "matched." Restricting auto-grading to numbers — where "does this number
appear in the answer" is unambiguous — avoids introducing exactly the kind of unreliable
heuristic that would undermine trust in every "matched" the report shows. Reusing
`data_access.numeric.parse_locale_number` (rather than writing a second locale-number parser)
is Principle V/"don't duplicate mechanism" applied directly — it already handles the
Brazilian/US separator ambiguity this exact testset's values are drawn from. Defining the
`MatchStrategy` `Protocol` now, with a single implementation, follows Engineering Principle 2's
own stated trigger ("every axis expected to vary gets a Protocol... defined before it needs to
vary") — FR-006 vs. FR-007 is explicitly, in the spec itself, an axis that varies by answer
shape, so the seam belongs at this feature's inception even though only one concrete strategy
ships now; a future short-exact-string strategy is then a new class, never a change to
`runner.py`'s caller code.

**Alternatives considered**: Auto-grading short strings via case/whitespace-normalized exact or
substring match was prototyped against this feature's own bundled testset and rejected — every
non-numeric `expected` value in the 50-question sample is either a composite multi-field
string or descriptive edge-case text, so the "short exact string" carve-out has no real example
to validate against today, and shipping an unvalidated heuristic risks silently wrong grades
that are strictly worse than routing to human review (the spec's own explicit fallback, FR-007).
Treating the leading `~` marker as decorative and requiring exact equality even for
approximate expected values was rejected — two of the bundled testset's own calculation-type
questions (`~3675300.51`, `~9898319.48`) are explicitly marked approximate, and exact-equality
grading against them would systematically mark a correct agent answer as `not_matched`.

## 6. Detecting "target unreachable for the whole run" is a run-level heuristic, not a `qa_agent` change

**Decision**: After a run completes, `testset_runner` inspects the aggregated
`QuestionResult`s: if every question that reached dataset selection successfully (i.e. every
question that is not itself an edge case in dataset selection) came back with `errored=True`
(§3), the `RunSummary` sets `target_unreachable=True` and its human-readable summary states
this plainly, instead of only listing 50 individually "errored" rows. Any run with at least one
non-errored result never sets this flag, even if many individual questions genuinely errored.

**Rationale**: The spec's Edge Cases explicitly call for a run-level signal, not a wall of
identical per-question errors, when "the configured model/URL is unreachable for the entire
run." `answer_question` intentionally never raises past its own boundary (`003`'s Tier 3
design, research.md §10) and this feature does not touch that guarantee — Tier 3's fixed
Portuguese fallback message plus the new `errored=True` flag (§3) is already sufficient
information for `testset_runner`, a layer above `qa_agent`, to recognize the "every question
failed the exact same way" pattern deterministically, without `qa_agent` itself needing to know
anything about testsets or runs (Principle V — this detection is testset-runner-specific
domain knowledge and belongs at this layer, not inside the general-purpose `qa_agent`).

**Alternatives considered**: Having `answer_question` distinguish connectivity failures from
other Tier 3 failures (e.g. a new `Literal["connectivity", "other"]` failure-kind field) was
considered and rejected as premature — no requirement needs `qa_agent` itself to react
differently to a connectivity failure specifically (vs. any other Tier 3 failure); the
all-or-nothing pattern across a whole run is what actually signals "the target itself is down,"
and only `testset_runner` has a "whole run" to look across in the first place.

## 7. Persistence: one JSON file per completed run, written exactly once, testset identity by content hash

**Decision**: A completed `TestRun` is serialized as a single JSON file at
`data/testset_runs/<run_id>.json` (`run_id` = an ISO-8601-based, filesystem-safe timestamp,
e.g. `20260918T153000Z`), written by `testset_runner.store.RunStore.save` exactly once, after
every question in the loop (§2) has produced a `QuestionResult` — never incrementally. A
`Testset` carries both its source `path` and a `content_hash` (SHA-256 over the file's raw
bytes, computed once at load time); every persisted `TestRun` stores its `Testset`'s
`content_hash` alongside its `path`, so two runs against files that share a name but differ in
content are never treated as the same testset (FR-011, Edge Cases). No API key or other
credential field is ever written into a run file (Constitution Principle VIII) — only
`model_name` and (if set) `base_url` are recorded in `TargetConfiguration`.

**Rationale**: Writing the whole run file exactly once, only after the full loop finishes,
directly satisfies the "a run interrupted partway... not presented as if it were a complete
run" edge case for free: if the process is killed mid-run, no file exists yet at all, so there
is nothing to mistake for a finished report — no separate atomic-write/rename scheme or
in-progress marker is needed. One file per run (rather than one growing JSONL log, unlike
`002`/`003`'s append-only per-question logs) matches this entity's actual shape: a `TestRun` is
a single, coherent, richly-structured object (summary + N nested per-question results), not a
stream of independent same-shaped log rows — JSONL's benefit (crash-safe partial durability)
is exactly what the "no partial report" requirement says *not* to offer here. Content-hashing
the testset file is the only reliable way to satisfy FR-011's explicit requirement to record
"which testset (including its version/content, not just its file name)" — a `path` alone
cannot detect that the file was edited between two runs.

**Alternatives considered**: Appending one JSONL line per question as the run progresses (then
a separate "run complete" marker) was rejected per the atomicity reasoning above — it would
require *additional* logic (a completion flag, and callers needing to check it) to recover the
same guarantee that "write once, at the end" gives for free. Storing runs in a single shared
JSONL file (one line per run) was rejected — a `TestRun` with 50 nested `QuestionResult`s
(each with a variable-length `steps` list) is exactly the "richly structured, individually
retrieved" shape a one-file-per-record layout serves better than a shared log, and a person
"revisiting" a specific run (FR-009) benefits from a single self-contained, directly-openable
file. `data/testset_runs/` is added to `.gitignore` alongside the existing `data/logs/` entry —
generated run artifacts, not source data, same reasoning as `002`/`003`'s logs.

## 8. Comparison: hash-gated, and every question is accounted for, not just the changed ones

**Decision**: `testset_runner.comparator.compare_runs(run_a: TestRun, run_b: TestRun) ->
RunComparison` first checks `run_a.testset.content_hash == run_b.testset.content_hash`; on a
mismatch it raises `IncompatibleRunsError` (never silently produces a diff). On a match, it
builds one `ComparisonEntry` per question `n` present in both runs, each carrying
`status_a`, `status_b`, and a derived `transition: Literal["newly_passing", "newly_failing",
"still_passing", "still_failing", "unchanged_other"]` (the last covering pairs like
`needs_review → needs_review` or `errored → errored`, where "passing/failing" doesn't cleanly
apply). `RunComparison.summary` reports counts for every transition bucket, so the total always
equals the question count — nothing is dropped from the report even when unchanged.

**Rationale**: FR-010 asks for "which questions changed match status," but SC-003 additionally
requires that "a person reviewing the comparison does not need to manually re-check any
unchanged question to trust the comparison is complete" — which is only possible if unchanged
questions are explicitly counted, not merely omitted from a "changed" list (an omission looks
identical to "the tool forgot to check this one"). Gating on `content_hash` rather than
`testset.path` is what makes FR-011's "two runs made from testsets that are not the same set of
questions... tells them the runs aren't directly comparable" edge case actually catch an edited
file with the same name, not just a differently-named one.

**Alternatives considered**: Comparing by `testset.path` equality alone was rejected as
insufficient for the exact edge case the spec calls out ("same name, different content").
Silently comparing only the question IDs present in both runs and ignoring the rest (a partial
diff) was rejected — it would violate FR-011's "MUST warn rather than silently proceed" for any
testset mismatch, not just a completely disjoint one.

## 9. CLI surface: explicit flags per invocation, not env-vars-only

**Decision**: `python -m testset_runner.cli run --testset <path> --model <model_name>
[--base-url <url>] [--api-key <key>] [--out-dir data/testset_runs]` runs a full testset and
prints a one-screen summary (match rate, per-category breakdown, `target_unreachable` warning
if set) plus the saved run file's path. `python -m testset_runner.cli compare <run_a.json>
<run_b.json>` loads two saved runs and prints the comparison. Every flag has a corresponding
`QA_AGENT_*`-prefixed environment-variable fallback (reusing `AgentSettings`, §4) for scripted/
CI-style use, but the CLI flags exist specifically so two different runs in the same shell
session never require re-exporting an environment variable between them.

**Rationale**: US3's own wording is explicit: "without editing source files or wiring up new
environment variables by hand each time" — `003`'s env-var-only `AgentSettings` construction
(`eval_harness.py`'s pattern) satisfies "no source edits" but not "no re-wiring env vars each
time" when comparing two targets back to back, which is this feature's whole User Story 2/3
point. Flags are the natural per-invocation mechanism; keeping the env-var fallback avoids
throwing away `003`'s existing configuration path or forcing every future automated caller to
pass everything explicitly.

**Alternatives considered**: Env-vars-only (matching `eval_harness.py` exactly) was rejected for
the reason above. A YAML/JSON run-config file was rejected as more machinery than a ~5-flag CLI
needs today — nothing in the spec calls for saved, named target presets.

## 10. Testing strategy: a fake `QuestionAnswerer` for fast/deterministic coverage, `FunctionModel` for one true end-to-end check

**Decision**: Most `testset_runner` contract/unit tests (loader validation, matcher grading
rules, comparator transitions, store round-trips, run-level `target_unreachable` detection)
inject a hand-written fake implementing the `QuestionAnswerer` Protocol (§1) that returns
scripted `QuestionAnsweringResult`s per question — no `pydantic-ai` object, no network, mirrors
how `dataset_selector`'s own tests fake `DatasetSelector`. One additional contract test drives
the real `qa_agent.capabilities.answer_question` (via the real `QaAgentQuestionAnswerer`
adapter) with a scripted `pydantic_ai.models.function.FunctionModel`, over the real bundled
`data/testsets/...json`'s first few questions, proving the adapter wiring itself — not just the
fake — actually produces a well-formed `QuestionResult` including a non-empty `steps` list.

**Rationale**: Mirrors `003`'s own established split (deterministic contract tests vs. a
documented live-model track, research.md §11): `testset_runner`'s *own* logic (grading,
comparing, persisting) has nothing to do with real model quality and should be tested at full
speed with no network, per Engineering Principle 6 ("tool functions... testable without a
model" — extended here to "orchestration logic testable without a model"). The one
`FunctionModel`-driven adapter test exists because §3's new `steps`/`errored` extraction logic
is genuinely new code inside `qa_agent.capabilities` that the fake cannot exercise (a fake
never calls `run_result.all_messages()`), and Constitution Principle IV requires that new
behavior be demonstrated by a real test, not assumed correct by inspection.

**Alternatives considered**: Testing `testset_runner` exclusively through the real `qa_agent`
adapter (no fake) was rejected — it would make every loader/matcher/comparator test pay the
cost (and `FunctionModel` scripting complexity) of a full agent run for logic that has nothing
to do with the agent at all, working against fast, focused unit tests (Principle IV).

## 11. Type checker and test framework

**Decision**: `pyright` (CI) and `pytest`, unchanged from `001`/`002`/`003`.

**Rationale**: Consistency; nothing in this feature's requirements motivates a different choice.
