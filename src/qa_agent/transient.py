"""Transient vs. non-transient failure classification (006 research.md §3).

The only module of the 006 feature that imports `pydantic_ai`; everything else about
describing a failure lives framework-free in `qa_agent.failures`.

A failure is **transient** if *any* link of its cause chain matches one of:

| Rule                                                                  | Covers                                  |
|-----------------------------------------------------------------------|-----------------------------------------|
| `ModelHTTPError` with `status_code` in {408, 425, 429}, or 5xx but 501 | request timeout, rate limit, server/overload errors |
| `ModelAPIError` that is not a `ModelHTTPError`                        | connection failures and timeouts, as `pydantic-ai` wraps them |
| built-in `TimeoutError`, `ConnectionError` (and subclasses)            | the same, from providers that do not wrap them |

"Any link" rather than "the root" because the root is usually a provider-SDK or `httpx`
type we deliberately do not name, while the `pydantic-ai` wrapper carrying `status_code`
sits one level up. Anything unrecognized is **non-transient** (FR-011): retrying an
auth error, an unknown model or an agent-behavior outcome (`UnexpectedModelBehavior`,
`UsageLimitExceeded`) only wastes time.

`retry_after_seconds` is the first `ModelHTTPError.retry_after` found in the chain.
"""

from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError

from qa_agent.failures import TransientVerdict, iter_chain

__all__ = ["TransientVerdict", "classify"]

_TRANSIENT_4XX = frozenset({408, 425, 429})


def classify(exc: BaseException) -> TransientVerdict:
    transient = False
    retry_after: float | None = None
    for link in iter_chain(exc):
        if _is_transient_link(link):
            transient = True
        if retry_after is None and isinstance(link, ModelHTTPError):
            link_retry_after = link.retry_after
            if link_retry_after is not None:
                retry_after = float(link_retry_after)
    if not transient:
        return TransientVerdict(False, None)
    return TransientVerdict(True, retry_after)


def _is_transient_link(link: BaseException) -> bool:
    if isinstance(link, ModelHTTPError):
        code = link.status_code
        return code in _TRANSIENT_4XX or (500 <= code <= 599 and code != 501)
    if isinstance(link, ModelAPIError):
        return True
    return isinstance(link, (TimeoutError, ConnectionError))
