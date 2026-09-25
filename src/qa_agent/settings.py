"""AgentSettings: the first typed settings object in this codebase (Eng. Principle 7)."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
