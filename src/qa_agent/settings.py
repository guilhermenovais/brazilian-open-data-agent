"""AgentSettings: the first typed settings object in this codebase (Eng. Principle 7)."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from qa_agent.prompt_loader import DEFAULT_PROMPT_VERSION, check_version


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QA_AGENT_")

    model_name: str
    instrument: bool = True
    base_url: str | None = None
    api_key: str | None = None
    prompt_version: str = Field(
        default=DEFAULT_PROMPT_VERSION,
        description="Prompt version (file prompts/system_<version>.md); default v2",
    )

    @field_validator("prompt_version")
    @classmethod
    def _known_prompt_version(cls, value: str) -> str:
        check_version(value)
        return value
