"""Unit tests for qa_agent.failures: chain walking, redaction, truncation (006 research.md §4-§6)."""

import pytest

from qa_agent.failures import (
    MAX_MESSAGE_CHARS,
    TransientVerdict,
    describe_failure,
    never_transient,
    redact,
    root_cause,
    truncate,
)

SECRET = "sk-test-DO-NOT-LEAK-1234567890"


def _raise_from(outer: BaseException, inner: BaseException) -> BaseException:
    try:
        try:
            raise inner
        except BaseException as caught:
            raise outer from caught
    except BaseException as final:
        return final


# --- root_cause -----------------------------------------------------------------------


def test_root_cause_follows_explicit_cause() -> None:
    exc = _raise_from(RuntimeError("outer"), TimeoutError("inner"))
    root = root_cause(exc)
    assert isinstance(root, TimeoutError)


def test_root_cause_falls_back_to_implicit_context() -> None:
    try:
        try:
            raise KeyError("inner")
        except KeyError:
            raise ValueError("outer")
    except ValueError as exc:
        caught = exc
    assert isinstance(root_cause(caught), KeyError)


def test_root_cause_ignores_context_when_suppressed() -> None:
    try:
        try:
            raise KeyError("inner")
        except KeyError:
            raise ValueError("outer") from None
    except ValueError as exc:
        caught = exc
    assert root_cause(caught) is caught


def test_root_cause_stops_on_a_cycle() -> None:
    a = RuntimeError("a")
    b = RuntimeError("b")
    a.__cause__ = b
    b.__cause__ = a
    assert root_cause(a) is b


def test_root_cause_of_an_unchained_exception_is_itself() -> None:
    exc = ValueError("alone")
    assert root_cause(exc) is exc


# --- redact ---------------------------------------------------------------------------


def test_redact_replaces_an_exact_configured_secret() -> None:
    assert redact(f"bad key {SECRET} given", [SECRET]) == "bad key [REDACTED] given"


def test_redact_replaces_an_exact_secret_that_matches_no_pattern() -> None:
    assert redact("echo plainsecretvalue here", ["plainsecretvalue"]) == "echo [REDACTED] here"


def test_redact_ignores_none_and_empty_secrets() -> None:
    assert redact("Connection refused", [None, ""]) == "Connection refused"


@pytest.mark.parametrize(
    "text",
    [
        "Authorization failed: Bearer abc.def-123",
        "invalid key sk-abcdefghijklmnopqrstuvwx",
        "api_key=abc123",
        "api-key: abc123",
        "apikey=abc123",
        "token=abc123",
        "authorization: abc123",
        "key=abc123",
    ],
)
def test_redact_pattern_pass_removes_credential_shapes(text: str) -> None:
    redacted = redact(text, [])
    assert "abc" not in redacted
    assert "[REDACTED]" in redacted


def test_redact_leaves_ordinary_text_unchanged() -> None:
    assert redact("Connection refused", []) == "Connection refused"


# --- truncate -------------------------------------------------------------------------


def test_truncate_leaves_a_message_at_the_limit_unchanged() -> None:
    message = "x" * MAX_MESSAGE_CHARS
    assert truncate(message) == message


def test_truncate_cuts_a_long_message_and_marks_it() -> None:
    message = "x" * 2500
    assert truncate(message) == "x" * 2000 + "… [truncated 500 characters]"


def test_truncate_keeps_an_empty_message_empty() -> None:
    assert truncate("") == ""


# --- describe_failure -----------------------------------------------------------------


def test_describe_failure_takes_type_and_message_from_the_root() -> None:
    exc = _raise_from(RuntimeError("outer"), TimeoutError("read timed out"))
    detail = describe_failure(exc, secrets=[], classify=never_transient)
    assert detail.type == "TimeoutError"
    assert detail.message == "read timed out"


def test_describe_failure_redacts_before_truncating() -> None:
    message = "x" * (MAX_MESSAGE_CHARS - 10) + SECRET
    detail = describe_failure(ValueError(message), secrets=[SECRET], classify=never_transient)
    assert "sk-test" not in detail.message
    assert "DO-NOT" not in detail.message


def test_describe_failure_classifies_the_original_exception_not_the_root() -> None:
    exc = _raise_from(RuntimeError("outer"), TimeoutError("inner"))
    seen: list[BaseException] = []

    def classify(e: BaseException) -> TransientVerdict:
        seen.append(e)
        return TransientVerdict(True, 12.0)

    detail = describe_failure(exc, secrets=[], classify=classify)
    assert seen == [exc]
    assert detail.transient is True
    assert detail.retry_after_seconds == 12.0


def test_describe_failure_keeps_an_empty_message() -> None:
    detail = describe_failure(ValueError(), secrets=[], classify=never_transient)
    assert detail.message == ""
    assert detail.transient is False
