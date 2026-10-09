"""Unit tests for AgentSettings.prompt_version (008 contracts/prompt-version-and-run-record.md)."""

import pydantic
import pytest

from qa_agent.settings import AgentSettings


def test_008_us4_1_default_prompt_version_is_v2(monkeypatch) -> None:
    monkeypatch.delenv("QA_AGENT_PROMPT_VERSION", raising=False)
    assert AgentSettings(model_name="m").prompt_version == "v2"


def test_008_us4_prompt_version_from_env(monkeypatch) -> None:
    monkeypatch.setenv("QA_AGENT_PROMPT_VERSION", "v1")
    assert AgentSettings(model_name="m").prompt_version == "v1"


def test_008_us4_3_invalid_prompt_version_rejected(monkeypatch) -> None:
    monkeypatch.delenv("QA_AGENT_PROMPT_VERSION", raising=False)
    with pytest.raises(pydantic.ValidationError) as exc_info:
        AgentSettings(model_name="m", prompt_version="v9")
    message = str(exc_info.value)
    assert "v9" in message
    assert "v1, v2, v3" in message
