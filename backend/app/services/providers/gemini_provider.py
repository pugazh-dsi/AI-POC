"""Google Gemini chat connector."""

from typing import Iterator

from google import genai
from google.genai import types
from google.genai import errors as genai_errors

from app.config import TEMPERATURE, MAX_ANSWER_TOKENS
from app.services.providers.base import ChatProvider, ProviderError, usage_dict


class GeminiChatProvider(ChatProvider):
    id = "gemini"
    label = "Google Gemini"

    def __init__(self, model: str, api_key: str):
        super().__init__(model)
        if not api_key:
            raise ProviderError("Google Gemini API key is not configured.")
        self._client = genai.Client(api_key=api_key)

    def _config(self, system: str) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=system,
            temperature=TEMPERATURE,
            max_output_tokens=MAX_ANSWER_TOKENS,
        )

    @staticmethod
    def _usage_of(response) -> dict:
        meta = getattr(response, "usage_metadata", None)
        if meta is None:
            return usage_dict(0, 0)
        return usage_dict(
            meta.prompt_token_count or 0,
            meta.candidates_token_count or 0,
        )

    def complete(self, system: str, user: str) -> dict:
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=user,
                config=self._config(system),
            )
        except genai_errors.APIError as e:
            raise ProviderError(str(e)) from e

        return {"text": response.text or "", "usage": self._usage_of(response)}

    def stream(self, system: str, user: str) -> Iterator[dict]:
        try:
            stream = self._client.models.generate_content_stream(
                model=self.model,
                contents=user,
                config=self._config(system),
            )

            usage = usage_dict(0, 0)
            for chunk in stream:
                if chunk.text:
                    yield {"type": "text", "content": chunk.text}
                if getattr(chunk, "usage_metadata", None):
                    usage = self._usage_of(chunk)
        except genai_errors.APIError as e:
            raise ProviderError(str(e)) from e

        yield {"type": "usage", "usage": usage}
