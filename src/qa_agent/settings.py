"""AgentSettings: the first typed settings object in this codebase (Eng. Principle 7)."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from data_access.text_matching import TextMatchingConfig
from qa_agent.prompt_loader import DEFAULT_PROMPT_VERSION, check_version


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QA_AGENT_")

    model_name: str
    instrument: bool = True
    base_url: str | None = None
    api_key: str | None = None
    # Characters of earlier visible turns sent with a conversational turn (FR-011). Only
    # `answer_turn` reads it; the standalone `answer_question` path ignores it. 16,000 holds
    # 20+ typical turns (~800 chars each, generously) in ~4-5k tokens (research.md R3, SC-006).
    history_char_limit: int = Field(default=16_000, ge=0)
    # Text filter matching, value suggestions and value lists (009 research.md R6). No env
    # var or CLI flag: the defaults are the evaluated values; runs record what was used.
    text_matching: TextMatchingConfig = Field(default_factory=TextMatchingConfig)
    prompt_version: str = Field(
        default=DEFAULT_PROMPT_VERSION,
        description="Prompt version (file prompts/system_<version>.md); default v2",
    )

    @field_validator("prompt_version")
    @classmethod
    def _known_prompt_version(cls, value: str) -> str:
        check_version(value)
        return value
