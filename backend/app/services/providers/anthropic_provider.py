"""Anthropic (Claude) chat connector."""

from typing import Iterator

import anthropic

from app.config import TEMPERATURE, MAX_ANSWER_TOKENS
from app.services.providers.base import ChatProvider, ProviderError, usage_dict

# Sampling parameters (temperature/top_p/top_k) were REMOVED on these models and
# return HTTP 400 if sent. The app's tuned TEMPERATURE is applied only where the
# model still accepts it.
NO_SAMPLING_MODELS = {
    "claude-fable-5",
    "claude-fable-5-1",
    "claude-opus-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-sonnet-5",
}

# Models that accept output_config.effort. Grounded document Q&A is not a deep
# reasoning task, so effort is pinned low to keep latency and cost down.
EFFORT_MODELS = NO_SAMPLING_MODELS | {"claude-opus-4-6", "claude-sonnet-4-6"}

# Server-side refusal fallbacks: if a safety classifier declines the request,
# the API transparently reroutes instead of returning an unusable response.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
FALLBACK_MODELS = {"claude-opus-5", "claude-fable-5", "claude-fable-5-1"}

REFUSAL_MESSAGE = (
    "This request was declined by the model's safety system. "
    "Try rephrasing your question about the document."
)


class AnthropicChatProvider(ChatProvider):
    id = "anthropic"
    label = "Anthropic (Claude)"

    def __init__(self, model: str, api_key: str):
        super().__init__(model)
        if not api_key:
            raise ProviderError("Anthropic API key is not configured.")
        self._client = anthropic.Anthropic(api_key=api_key)

    def _params(self, system: str, user: str) -> dict:
        params: dict = {
            "model": self.model,
            "max_tokens": MAX_ANSWER_TOKENS,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }

        if self.model in NO_SAMPLING_MODELS:
            # temperature would 400 here; steer cost with effort instead
            params["output_config"] = {"effort": "low"}
        else:
            params["temperature"] = TEMPERATURE
            if self.model in EFFORT_MODELS:
                params["output_config"] = {"effort": "low"}

        return params

    def _uses_fallbacks(self) -> bool:
        return self.model in FALLBACK_MODELS

    @staticmethod
    def _is_beta_rejection(error: Exception) -> bool:
        text = str(error).lower()
        return "beta" in text or "fallback" in text

    @staticmethod
    def _text_of(message) -> str:
        if getattr(message, "stop_reason", None) == "refusal":
            return REFUSAL_MESSAGE
        return "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )

    @staticmethod
    def _usage_of(message) -> dict:
        usage = message.usage
        return usage_dict(usage.input_tokens, usage.output_tokens)

    def complete(self, system: str, user: str) -> dict:
        params = self._params(system, user)
        try:
            if self._uses_fallbacks():
                try:
                    message = self._client.beta.messages.create(
                        **params, betas=[FALLBACK_BETA], fallbacks="default"
                    )
                except anthropic.APIStatusError as e:
                    if not self._is_beta_rejection(e):
                        raise
                    message = self._client.messages.create(**params)
            else:
                message = self._client.messages.create(**params)
        except anthropic.APIError as e:
            raise ProviderError(str(e)) from e

        return {"text": self._text_of(message), "usage": self._usage_of(message)}

    def stream(self, system: str, user: str) -> Iterator[dict]:
        params = self._params(system, user)

        def open_stream():
            if self._uses_fallbacks():
                try:
                    return self._client.beta.messages.stream(
                        **params, betas=[FALLBACK_BETA], fallbacks="default"
                    )
                except anthropic.APIStatusError as e:
                    if not self._is_beta_rejection(e):
                        raise
            return self._client.messages.stream(**params)

        try:
            with open_stream() as stream:
                for text in stream.text_stream:
                    yield {"type": "text", "content": text}

                final = stream.get_final_message()
                if final.stop_reason == "refusal":
                    yield {"type": "text", "content": REFUSAL_MESSAGE}
                yield {"type": "usage", "usage": self._usage_of(final)}
        except anthropic.APIError as e:
            raise ProviderError(str(e)) from e
