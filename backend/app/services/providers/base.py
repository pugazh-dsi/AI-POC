"""Common interface every chat provider implements."""

from abc import ABC, abstractmethod
from typing import Iterator


class ProviderError(RuntimeError):
    """Raised when a provider is misconfigured or its API rejects the call."""


class ChatProvider(ABC):
    """A chat-completion backend.

    Implementations must not change the RAG behaviour: they receive the already
    built system prompt and the XML-delimited user prompt, and return text.
    """

    id: str = ""
    label: str = ""

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def complete(self, system: str, user: str) -> dict:
        """Return {"text": str, "usage": {prompt_tokens, completion_tokens, total_tokens}}."""

    @abstractmethod
    def stream(self, system: str, user: str) -> Iterator[dict]:
        """Yield {"type": "text", "content": str} chunks, then one
        {"type": "usage", "usage": {...}} event when the response completes."""

    def check(self) -> None:
        """Make a minimal call to validate credentials. Raises ProviderError."""
        self.complete("Reply with OK.", "Say OK.")


def usage_dict(prompt_tokens: int, completion_tokens: int) -> dict:
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }
