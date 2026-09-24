"""The transient/non-transient classification table (006 research.md §3, FR-010/FR-011)."""

import pytest
from pydantic_ai.exceptions import (
    ModelAPIError,
    ModelHTTPError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)

from qa_agent.transient import classify


def _http(status_code: int, retry_after: str | None = None) -> ModelHTTPError:
    headers = {"Retry-After": retry_after} if retry_after is not None else None
    return ModelHTTPError(status_code=status_code, model_name="m", body=None, headers=headers)


def _chain(outer: BaseException, inner: BaseException) -> BaseException:
    outer.__cause__ = inner
    return outer


@pytest.mark.parametrize(
    "exc",
    [
        *[_http(code) for code in (408, 425, 429, 500, 502, 503, 504, 529)],
        ModelAPIError(model_name="m", message="Connection error."),
        TimeoutError("timed out"),
        ConnectionError("reset"),
        ConnectionRefusedError("refused"),
        _chain(UnexpectedModelBehavior("stream ended"), TimeoutError("read timed out")),
    ],
    ids=repr,
)
def test_transient_failures(exc: BaseException) -> None:
    assert classify(exc).transient is True


@pytest.mark.parametrize(
    "exc",
    [
        *[_http(code) for code in (400, 401, 403, 404, 409, 422, 501)],
        UnexpectedModelBehavior("Exceeded maximum retries for output validation"),
        UsageLimitExceeded("request limit of 50 exceeded"),
        ValueError("bad"),
        RuntimeError("bad"),
    ],
    ids=repr,
)
def test_non_transient_failures(exc: BaseException) -> None:
    verdict = classify(exc)
    assert verdict.transient is False
    assert verdict.retry_after_seconds is None


def test_retry_after_is_returned_unchanged() -> None:
    assert classify(_http(429, retry_after="30")).retry_after_seconds == 30.0


def test_retry_after_is_none_when_absent() -> None:
    assert classify(_http(429)).retry_after_seconds is None


def test_first_http_error_in_the_chain_carrying_a_retry_after_wins() -> None:
    exc = _chain(_http(503), _chain(_http(429, retry_after="7"), _http(429, retry_after="99")))
    verdict = classify(exc)
    assert verdict.transient is True
    assert verdict.retry_after_seconds == 7.0
