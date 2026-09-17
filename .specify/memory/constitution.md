<!--
Sync Impact Report
- Version change: TEMPLATE (unratified) → 1.0.0
- Rationale for MAJOR: initial ratification of a previously-unfilled template; establishes
  the full set of binding principles and governance rules for the first time.
- Modified principles: N/A (initial adoption, no prior ratified text existed)
- Added sections:
  - Core Principles I–X (research/scientific-integrity principles)
  - Python & pydantic-ai Engineering Principles (10 sub-principles)
  - Development Workflow
  - Governance (amendment procedure, versioning policy, compliance review)
- Removed sections: none
- Templates checked for consistency:
  - .specify/templates/plan-template.md ✅ Constitution Check gate is generic and
    references "constitution file" without hardcoding principle names — compatible as-is.
  - .specify/templates/spec-template.md ✅ no constitution-specific references; compatible.
  - .specify/templates/tasks-template.md ✅ no constitution-specific references; compatible.
  - .specify/templates/checklist-template.md ✅ generic; compatible.
  - .claude/skills/speckit-*/* ✅ no agent-specific (e.g. CLAUDE-only) references found.
  - No README.md or runtime guidance docs exist yet in this repo — nothing to update.
- Follow-up TODOs:
  - An untracked file `constitution.m` exists at the repository root containing the same
    raw text supplied as input to this command. It appears to be a stray artifact from an
    earlier/interrupted attempt and is not referenced by any tooling. Recommend the user
    delete it manually; this command does not remove files outside `.specify/`.
-->

# Brazilian Open Data Agent Constitution

## Core Principles

### I. Reproducibility Over One-Off Results
Any empirical claim about the system — accuracy, a comparison between models or
approaches, a measured improvement — MUST be backed by a pipeline that can be re-run and
re-verified, with inputs, outputs, and run conditions recorded. A manually-run,
hand-graded, one-time report MUST NOT be presented as a finding. A conclusion that cannot
be reproduced from recorded inputs and conditions is not treated as a finding, no matter
how it was obtained.

### II. Evidence Before Implementation
Changes to system behavior MUST be justified by a documented, reproduced observation —
a concrete failure case or a measured gap — not by speculation about what "should" help.
The decision and the evidence behind it MUST be written down where future contributors
can find them (specs, decision records, or results documents), not left only in a commit
message.

### III. Documentation Is a Deliverable
Every module, decision, and result MUST be documented well enough that someone outside
the original work can understand what was built, why it was built that way, and what
alternatives were rejected and why. This applies equally to code — clear structure,
meaningful names, docstrings where intent isn't obvious — and to the project's research
record: specs, decisions, and results. Undocumented work is incomplete work.

### IV. Tests Document Behavior
The test suite MUST be readable as a specification of what the system guarantees. Tests
that state a behavior clearly — arrange/act/assert, meaningful names and cases — are
favored over tests that merely pin current output. A new contributor MUST be able to
learn how the system behaves largely by reading the tests, without reading the
implementation first.

### V. Separate Mechanism from Domain Knowledge
The core system MUST NOT encode facts specific to one dataset, one model, or one
deployment. Anything specific to a particular case — a dataset's schema quirks, a
model's prompt, a deployment's credentials — lives in configuration or data artifacts,
never in the general codebase. The system generalizes by default; anything that doesn't
generalize is an exception that lives outside the core.

### VI. Deterministic Computation Over Model Judgment
Wherever a result can be computed or verified mechanically, it MUST be computed
mechanically rather than left to model judgment. Model-driven reasoning is reserved for
genuine judgment calls the system cannot resolve deterministically — e.g., interpreting
an ambiguous natural-language question — not for tasks like arithmetic, filtering, or
schema matching that have a deterministic answer.

### VII. Code Quality Is Enforced
Consistent style, linting, type checking, and code review are part of how changes land,
not optional polish applied later. Simplicity is a constraint: no speculative
abstraction and no unused generality ahead of actual, demonstrated need. A change that
adds complexity without a present requirement for it MUST be rejected or simplified.

### VIII. Security and Data Stewardship Are Non-Negotiable
Credentials MUST NEVER be stored in the working tree. Secret-handling (how credentials
are supplied, rotated, and scoped) MUST be verified before it is needed — designed and
reviewed up front — not retrofitted after an incident.

### IX. Continuous Integration Gate
CI MUST run tests and linting/type-checks on every change. Documentation and tests are
part of the definition of done for a change; a change that lacks either is not done, and
MUST NOT merge on the promise of a follow-up.

### X. Usage as Research Data
Because this is a research system, its own usage — questions asked, decisions made by
the agent, outcomes observed — MUST be captured systematically, not incidentally. This
usage record is itself data the project relies on, and its collection is a first-class
design concern, not an operational afterthought.

## Python & pydantic-ai Engineering Principles

These principles govern how the Core Principles above are realized in this project's
Python / pydantic-ai codebase specifically. They are subordinate to, and exist to serve,
the Core Principles — most directly Reproducibility (I), Separation of Mechanism from
Domain Knowledge (V), and Code Quality (VII).

1. **Orchestration is a thin wiring layer.** `Agent`, tool registration, `RunContext`,
   and prompt assembly stay in a small integration layer (e.g. `tools.py`/`app.py`). All
   actual logic — parsing, schema detection, querying — lives in plain,
   framework-agnostic Python with no `pydantic-ai` import, so switching agent frameworks
   or running the same logic outside an LLM loop (e.g. for an automated validation
   harness) never requires touching business logic.
2. **Define an interface before the second implementation.** Every axis expected to
   vary gets a `Protocol`/`ABC` defined before it needs to vary: a `QueryEngine`
   protocol (`query_rows`, `aggregate`) with a `PandasQueryEngine` today and room for a
   `DuckDBQueryEngine` later; a `ModelProvider`/model-config abstraction so OpenAI,
   OpenRouter, and local vLLM are all "just configuration"; a `BriefingSource`
   abstraction so manual and auto-generated briefings are interchangeable. Trying a new
   approach MUST mean writing a new class against an existing interface, never editing
   callers.
3. **Format/backend dispatch is polymorphic, not branching.** `if csv elif json`-style
   dispatch is replaced by one implementation per format behind a shared interface, so
   adding a third format is additive, not a growing conditional.
4. **Dependency injection over globals.** The active dataset, query engine, and model
   config are injected per run via `RunContext[Deps]`, not fixed once at process start
   via a module-level global or an env read buried in a function. Swapping the dataset
   or backend MUST be a parameter, not a restart.
5. **Every tool boundary is a validated pydantic model.** Tool input/output MUST be
   pydantic models validated at the boundary; no untyped dicts cross it. This is what
   lets a tool's internal implementation change freely as long as its contract doesn't,
   and what makes tool behavior testable without a model in the loop.
6. **Tool functions are unit-testable without a model.** The `@agent.tool` wrapper is a
   thin adapter over a plain function, and that plain function is what gets tested. A
   new query engine or parsing strategy MUST be benchmarkable directly, without a full
   agent run.
7. **Configuration is a typed, centralized object.** Settings are expressed via
   `pydantic-settings`, not scattered `os.environ` reads. Every experiment — a
   different model, dataset, or tool implementation — MUST be expressible as an
   explicit, recorded settings object, feeding directly into Core Principle I
   (Reproducibility): a run's exact configuration must always be reconstructable.
8. **Prompts and tool schemas are versioned artifacts.** Prompt/briefing content is
   treated like a model checkpoint: named, diffable, and referenced explicitly by the
   run configuration that used it — never edited in place.
9. **Prefer native instrumentation over bespoke logging.** Use pydantic-ai's built-in
   tracing (Logfire/OpenTelemetry) of model calls, tool calls, and validation retries
   rather than hand-rolled logging, keeping Core Principle X (usage as research data)
   nearly free to satisfy.
10. **Static typing is enforced, not advisory.** Full type hints and a type checker
    (mypy or pyright) run in CI, since the interfaces required by principles 2–5 only
    deliver on "safe to swap" if a broken contract is caught before runtime.

## Development Workflow

Every feature proceeds through the spec-kit lifecycle: `/speckit-constitution` →
`/speckit-specify` → `/speckit-clarify` (as needed) → `/speckit-plan` →
`/speckit-tasks` → `/speckit-implement`, with `/speckit-analyze` available to check
cross-artifact consistency before implementation begins.

- The **Constitution Check** gate in `plan.md` MUST be evaluated before Phase 0 research
  and re-checked after Phase 1 design. Any violation MUST be recorded in that plan's
  Complexity Tracking table with the specific need and why a simpler alternative was
  rejected (Core Principle VII).
- A pull request's definition of done includes: passing CI (tests, linting, type
  checks — Principles VII, IX, and Engineering Principle 10), updated documentation for
  any behavior change (Principle III), and tests that read as a specification of the
  new or changed behavior (Principle IV).
- Any change to agent behavior grounded in an accuracy or comparison claim MUST link to
  the reproducible pipeline/run that produced it (Principle I) and the observation that
  motivated it (Principle II) — a spec's "Evidence" reference or a results document, not
  a commit message alone.

## Governance

This constitution supersedes all other project practices; where a documented practice
conflicts with it, the constitution governs and the practice MUST be updated or an
explicit, justified exception recorded (see Complexity Tracking above).

**Amendment procedure**: Amending this document requires a written rationale — what
changed and why — held to the same evidentiary bar as Core Principle II. Every amendment
MUST be recorded as a Sync Impact Report prepended to this file (as an HTML comment)
describing the version change, the principles added/modified/removed, and any templates
or docs updated in consequence.

**Versioning policy**: This constitution is versioned independently using semantic
versioning:
- **MAJOR** — backward-incompatible governance or principle removals/redefinitions.
- **MINOR** — a new principle or section added, or existing guidance materially expanded.
- **PATCH** — clarifications, wording, typo fixes, and other non-semantic refinements.

**Compliance review**: Every plan produced by `/speckit-plan` MUST pass the Constitution
Check gate described under Development Workflow. Reviewers MUST treat an unresolved
Constitution Check violation, a missing CI gate, or an unreproducible empirical claim as
blocking, not advisory.

**Version**: 1.0.0 | **Ratified**: 2026-09-17 | **Last Amended**: 2026-09-17
