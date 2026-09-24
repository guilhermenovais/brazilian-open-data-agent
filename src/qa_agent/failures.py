"""Turning a caught exception into a `FailureDetail` (006 research.md §4-§6).

Framework-agnostic on purpose: no pydantic-ai import (Engineering Principle 1). The
`pydantic-ai`-aware transient rules live in `qa_agent.transient` and are injected into
`describe_failure` as its `classify` callable.

- **Root cause (§4)**: the cause chain is walked from the caught exception — `__cause__`,
  else `__context__` unless `__suppress_context__` — stopping at the end or on a cycle.
  The recorded `type`/`message` are those of the last (root) link, because the outermost
  wrapper (`ModelHTTPError`, `ModelAPIError`) would collapse every provider failure into
  one summary bucket. The bare class name (`type(root).__name__`), not the qualname, is
  recorded: it reads well in a report and survives private-module moves such as
  `openai._exceptions`.
- **Redact, then truncate (§5, §6)**: every configured secret is removed exactly, then
  generic credential shapes are masked, and only then is the text capped at
  `MAX_MESSAGE_CHARS`. Truncating first could split a key and let its prefix survive the
  exact pass.
"""

import re
from collections.abc import Callable, Iterable, Iterator
from typing import NamedTuple

from qa_agent.models import FailureDetail

MAX_MESSAGE_CHARS = 2000
_REDACTED = "[REDACTED]"

# Best-effort safety net for credentials not handed to us directly (e.g. read by the
# provider SDK from its own environment variable). Each keeps its label and masks the value.
_CREDENTIAL_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(Bearer)\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE), rf"\1 {_REDACTED}"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"), _REDACTED),
    (
        re.compile(
            r"""\b(api[_-]?key|token|authorization|key)(["']?\s*[:=]\s*["']?)[^\s,;&"'}]+""",
            re.IGNORECASE,
        ),
        rf"\1\2{_REDACTED}",
    ),
)


class TransientVerdict(NamedTuple):
    """Whether a failure is worth retrying, and the provider's suggested wait if any."""

    transient: bool
    retry_after_seconds: float | None


def iter_chain(exc: BaseException) -> Iterator[BaseException]:
    """Yields `exc` and each exception it was caused by, outermost first, ending on a cycle."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        if current.__cause__ is not None:
            current = current.__cause__
        elif not current.__suppress_context__:
            current = current.__context__
        else:
            current = None


def root_cause(exc: BaseException) -> BaseException:
    root = exc
    for link in iter_chain(exc):
        root = link
    return root


def redact(message: str, secrets: Iterable[str | None]) -> str:
    for secret in secrets:
        if secret:
            message = message.replace(secret, _REDACTED)
    for pattern, replacement in _CREDENTIAL_PATTERNS:
        message = pattern.sub(replacement, message)
    return message


def truncate(message: str, limit: int = MAX_MESSAGE_CHARS) -> str:
    if len(message) <= limit:
        return message
    return f"{message[:limit]}… [truncated {len(message) - limit} characters]"


def describe_failure(
    exc: BaseException,
    *,
    secrets: Iterable[str | None],
    classify: Callable[[BaseException], TransientVerdict],
) -> FailureDetail:
    """Builds a `FailureDetail` from the root cause; `classify` sees the whole chain (`exc`)."""
    root = root_cause(exc)
    verdict = classify(exc)
    return FailureDetail(
        type=type(root).__name__,
        message=truncate(redact(str(root), secrets)),
        transient=verdict.transient,
        retry_after_seconds=verdict.retry_after_seconds,
    )


def never_transient(exc: BaseException) -> TransientVerdict:
    """The classifier for failures that are never worth retrying (e.g. dataset selection)."""
    return TransientVerdict(False, None)
