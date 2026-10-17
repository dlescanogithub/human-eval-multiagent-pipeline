from __future__ import annotations

import json
import urllib.request
from typing import Any

from hemp.errors import ConfigError, SchemaError
from hemp.models import Usage
from hemp.providers.base import Completion, CompletionRequest
from hemp.providers.cassette import CassetteProvider


class OpenAICompatProvider:
    """Optional adapter. Construction fails unless the network flag is explicit.

    CI and the default demo never construct this class. The live HTTP call is not
    part of the test suite.
    """

    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        allow_network: bool,
    ) -> None:
        if not allow_network:
            raise ConfigError("OpenAI-compatible adapter is off. Set HEMP_ALLOW_NETWORK=1 to use it outside CI.")
        if not api_key.strip():
            raise ConfigError("OPENAI_API_KEY is empty")
        if not model.strip():
            raise ConfigError("HEMP_MODEL is empty")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.allow_network = allow_network

    def build_body(self, request: CompletionRequest) -> dict[str, Any]:
        return {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return one JSON object for the requested step. The domain is fictional and synthetic."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "role": request.role,
                            "step": request.step,
                            "payload": request.payload,
                        },
                        sort_keys=True,
                    ),
                },
            ],
        }

    def complete(self, request: CompletionRequest) -> Completion:
        if not self.allow_network:
            raise ConfigError("network disabled")
        body = json.dumps(self.build_body(request)).encode("utf-8")
        http_request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(http_request, timeout=30) as response:  # pragma: no cover
            payload = json.loads(response.read().decode("utf-8"))
        content = parse_chat_response(payload)
        usage_raw = payload.get("usage", {}) if isinstance(payload, dict) else {}
        prompt = int(usage_raw.get("prompt_tokens", 0)) if isinstance(usage_raw, dict) else 0
        completion_tokens = int(usage_raw.get("completion_tokens", 0)) if isinstance(usage_raw, dict) else 0
        return Completion(
            content=content,
            usage=Usage(prompt, completion_tokens),
            provider=self.name,
            model=self.model,
        )


def parse_chat_response(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SchemaError("vendor payload must be an object")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise SchemaError("vendor payload has no choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise SchemaError("choice must be an object")
    message = first.get("message")
    if not isinstance(message, dict):
        raise SchemaError("message must be an object")
    content = message.get("content")
    if not isinstance(content, str):
        raise SchemaError("message content must be a string")
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise SchemaError("model content must be a JSON object")
    return parsed


def build_provider(
    *,
    provider: str,
    allow_network: bool,
    api_key: str,
    base_url: str,
    model: str,
    cassette_path: str,
) -> CassetteProvider | OpenAICompatProvider:
    if provider == "cassette":
        from pathlib import Path

        return CassetteProvider.load(Path(cassette_path))
    if provider == "openai":
        return OpenAICompatProvider(
            api_key=api_key,
            base_url=base_url,
            model=model,
            allow_network=allow_network,
        )
    raise ConfigError(f"unknown provider {provider}")
