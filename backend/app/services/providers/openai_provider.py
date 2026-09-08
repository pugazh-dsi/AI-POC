"""OpenAI and Azure OpenAI chat connectors (both use the `openai` package)."""

import json
from typing import Iterator, List, Dict

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

    # ── Tool calling ──────────────────────────────────────────────
    # Kept separate from stream() so the RAG path is untouched.

    @staticmethod
    def _to_wire(messages: List[Dict], system: str) -> List[Dict]:
        """Map the neutral message shape onto OpenAI's chat format."""
        wire: List[Dict] = [{"role": "system", "content": system}]

        for msg in messages:
            if msg["role"] == "tool":
                wire.append({
                    "role": "tool",
                    "tool_call_id": msg["tool_call_id"],
                    "content": msg["content"],
                })
            elif msg.get("tool_calls"):
                wire.append({
                    "role": "assistant",
                    "content": msg.get("content") or None,
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["args"]),
                            },
                        }
                        for tc in msg["tool_calls"]
                    ],
                })
            else:
                wire.append({"role": msg["role"], "content": msg["content"]})

        return wire

    def stream_tools(
        self, system: str, messages: List[Dict], tools: List[Dict]
    ) -> Iterator[Dict]:
        wire = self._to_wire(messages, system)

        try:
            stream = self._client.chat.completions.create(
                model=self.model,
                messages=wire,
                tools=[{"type": "function", "function": t} for t in tools],
                temperature=TEMPERATURE,
                max_tokens=MAX_ANSWER_TOKENS,
                stream=True,
            )
        except OpenAIError as e:
            raise ProviderError(str(e)) from e

        completion = ""
        # Tool call arguments arrive as fragments spread over many chunks and
        # are addressed by index, not id — so accumulate per index and only
        # parse the JSON once the stream is done.
        pending: Dict[int, Dict] = {}

        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if delta.content:
                completion += delta.content
                yield {"type": "text", "content": delta.content}

            for tc in delta.tool_calls or []:
                slot = pending.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                if tc.id:
                    slot["id"] = tc.id
                if tc.function and tc.function.name:
                    slot["name"] = tc.function.name
                if tc.function and tc.function.arguments:
                    slot["args"] += tc.function.arguments

        for index in sorted(pending):
            slot = pending[index]
            if not slot["name"]:
                continue
            try:
                args = json.loads(slot["args"]) if slot["args"].strip() else {}
            except json.JSONDecodeError:
                # A truncated argument fragment must not kill the turn — the
                # tool reports the bad input and the model can retry.
                args = {"__malformed__": slot["args"]}
            yield {
                "type": "tool_call",
                "id": slot["id"] or f"call_{index}",
                "name": slot["name"],
                "args": args,
            }

        # Streaming responses carry no usage block, so count locally — same
        # approach as stream().
        prompt_text = system + "".join(str(m.get("content") or "") for m in wire)
        yield {
            "type": "usage",
            "usage": usage_dict(count_tokens(prompt_text), count_tokens(completion)),
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
