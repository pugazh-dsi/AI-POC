"""OpenAI and Azure OpenAI chat connectors (both use the `openai` package)."""

from typing import Iterator

from openai import OpenAI, AzureOpenAI, OpenAIError

from app.config import TEMPERATURE, MAX_ANSWER_TOKENS
from app.services.context_builder import count_tokens
from app.services.providers.base import ChatProvider, ProviderError, usage_dict


class OpenAIChatProvider(ChatProvider):
    id = "openai"
    label = "OpenAI"

    def __init__(self, model: str, api_key: str, base_url: str = ""):
        super().__init__(model)
        if not api_key:
            raise ProviderError("OpenAI API key is not configured.")
        self._client = OpenAI(api_key=api_key, base_url=base_url or None)

    def _create(self, system: str, user: str, stream: bool):
        return self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_ANSWER_TOKENS,
            stream=stream,
        )

    def complete(self, system: str, user: str) -> dict:
        try:
            response = self._create(system, user, stream=False)
        except OpenAIError as e:
            raise ProviderError(str(e)) from e

        usage = response.usage
        return {
            "text": response.choices[0].message.content,
            "usage": usage_dict(usage.prompt_tokens, usage.completion_tokens),
        }

    def stream(self, system: str, user: str) -> Iterator[dict]:
        try:
            stream = self._create(system, user, stream=True)
        except OpenAIError as e:
            raise ProviderError(str(e)) from e

        completion = ""
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                completion += content
                yield {"type": "text", "content": content}

        # The streaming API doesn't return usage, so count locally (unchanged
        # from the original implementation).
        yield {
            "type": "usage",
            "usage": usage_dict(
                count_tokens(system) + count_tokens(user), count_tokens(completion)
            ),
        }


class AzureOpenAIChatProvider(OpenAIChatProvider):
    id = "azure_openai"
    label = "Azure OpenAI"

    def __init__(self, model: str, api_key: str, base_url: str, api_version: str):
        # `model` is the Azure *deployment* name, not the base model name
        ChatProvider.__init__(self, model)
        if not api_key:
            raise ProviderError("Azure OpenAI API key is not configured.")
        if not base_url:
            raise ProviderError("Azure OpenAI endpoint is required (e.g. https://<name>.openai.azure.com).")
        self._client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=base_url,
            api_version=api_version or "2024-10-21",
        )
