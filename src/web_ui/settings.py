"""WebServerSettings: host/port for the chat UI's HTTP server (data-model.md).

Kept separate from `qa_agent.settings.AgentSettings` (own env prefix, `QA_WEB_`) because
it governs a different concern — where the HTTP server listens, not which model answers
questions — even though both are constructed once per CLI invocation.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WebServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QA_WEB_")

    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
