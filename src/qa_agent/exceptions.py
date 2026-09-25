"""qa_agent's own exception types.

`UnknownPromptVersionError` subclasses `ValueError` so that `AgentSettings`'s pydantic
`field_validator` can raise it and have pydantic turn it into a `ValidationError`, while
callers that check a version directly (the CLIs, `QaAgentQuestionAnswerer`) can catch it
by its own type.
"""


class UnknownPromptVersionError(ValueError):
    """A prompt version was requested for which no `prompts/system_<version>.md` exists."""

    def __init__(self, requested: str, available: list[str]) -> None:
        self.requested = requested
        self.available = available
        super().__init__(
            f"unknown prompt version '{requested}' (available: {', '.join(available)})"
        )
