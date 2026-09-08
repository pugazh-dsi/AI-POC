"""Common interface every chat provider implements."""

from abc import ABC, abstractmethod
from typing import Iterator, List, Dict


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

    def stream_tools(
        self, system: str, messages: List[Dict], tools: List[Dict]
    ) -> Iterator[Dict]:
        """Multi-turn streaming with tool calling. Optional — the default raises.

        Unlike complete()/stream(), this takes the whole conversation so tool
        results can be fed back for a second pass, and `tools` as a list of
        JSON-Schema function definitions:

            {"name": str, "description": str, "parameters": {...}}

        Yields provider-agnostic events, so tool_service never sees a wire format:
            {"type": "text", "content": str}
            {"type": "tool_call", "id": str, "name": str, "args": dict}
            {"type": "usage", "usage": {...}}

        `messages` uses the OpenAI-ish neutral shape, which each provider maps
        onto its own format:
            {"role": "user"|"assistant", "content": str}
            {"role": "assistant", "tool_calls": [{"id", "name", "args"}]}
            {"role": "tool", "tool_call_id": str, "name": str, "content": str}
        """
        raise ProviderError(
            f"{self.label} tool calling is not wired up yet. "
            "Switch to OpenAI under Settings to use the Tool Calling tile."
        )

    def check(self) -> None:
        """Make a minimal call to validate credentials. Raises ProviderError."""
        self.complete("Reply with OK.", "Say OK.")


def usage_dict(prompt_tokens: int, completion_tokens: int) -> dict:
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }
