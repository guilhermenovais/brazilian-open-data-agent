"""AgentSettings: the first typed settings object in this codebase (Eng. Principle 7)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QA_AGENT_")

    model_name: str
    instrument: bool = True
    base_url: str | None = None
    api_key: str | None = None
