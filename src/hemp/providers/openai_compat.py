"""Optional live provider for an OpenAI-compatible chat-completions HTTP API.

Off unless ``LIVE_MODE=1`` and the live settings are all present. Demo, eval,
and CI do not construct a transport that opens a socket. No live result is
published from this module.
"""

from __future__ import annotations

import json
import logging
import random
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Protocol

from hemp.config import LiveConfig
from hemp.errors import ConfigError, ProviderError, SchemaError, TransientProviderError
from hemp.logging_setup import log_event
from hemp.models import Usage
from hemp.providers.base import Completion, CompletionRequest
from hemp.providers.cassette import CassetteProvider

LOGGER_NAME = "hemp.live"
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class Rng(Protocol):
    def random(self) -> float:
        """Return a float in [0.0, 1.0)."""


class Sleeper(Protocol):
    def __call__(self, seconds: float) -> None:
        """Pause for ``seconds``. Tests pass a recorder."""


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: dict[str, str]
    body: bytes


class Transport(Protocol):
    def __call__(self, url: str, body: bytes, headers: Mapping[str, str]) -> HttpResponse:
        """Perform one HTTP POST. The default implementation is not used in tests."""


def parse_retry_after(headers: Mapping[str, str], *, now_epoch: float | None = None) -> float | None:
    raw = ""
    for key, value in headers.items():
        if key.lower() == "retry-after":
            raw = value.strip()
            break
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    current = datetime.now(UTC).timestamp() if now_epoch is None else now_epoch
    return max(0.0, parsed.timestamp() - current)


def urllib_transport(url: str, body: bytes, headers: Mapping[str, str]) -> HttpResponse:  # pragma: no cover
    request = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")  # pragma: no cover
    try:  # pragma: no cover
        with urllib.request.urlopen(request, timeout=30) as response:  # pragma: no cover
            return HttpResponse(response.status, dict(response.headers), response.read())  # pragma: no cover
    except urllib.error.HTTPError as exc:  # pragma: no cover
        payload = exc.read()  # pragma: no cover
        return HttpResponse(exc.code, dict(exc.headers), payload)  # pragma: no cover
    except urllib.error.URLError as exc:  # pragma: no cover
        raise TransientProviderError("live transport failed") from exc  # pragma: no cover


class OpenAICompatProvider:
    """Chat-completions client. Retries are bounded, jittered, and honor Retry-After."""

    name = "openai-compatible"

    def __init__(
        self,
        config: LiveConfig,
        *,
        live_mode: bool,
        transport: Transport | None = None,
        sleep: Sleeper | None = None,
        rng: Rng | None = None,
        max_attempts: int = 3,
        backoff_base_seconds: float = 0.5,
        backoff_cap_seconds: float = 8.0,
        cassette_path: Path | None = None,
    ) -> None:
        if not live_mode:
            raise ConfigError("Live provider is off. Set LIVE_MODE=1 outside CI. This process will not call a model.")
        if max_attempts < 1:
            raise ConfigError("max_attempts must be at least 1")
        self.config = config
        self.transport = transport or urllib_transport
        self.sleep = sleep or (lambda _seconds: None)
        self.rng = rng or random.Random()
        self.max_attempts = max_attempts
        self.backoff_base_seconds = backoff_base_seconds
        self.backoff_cap_seconds = backoff_cap_seconds
        self.cassette_path = cassette_path
        self.spent_usd = 0.0
        self.waits: list[float] = []

    def build_body(self, request: CompletionRequest) -> dict[str, Any]:
        return {
            "model": self.config.model,
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
                        {"role": request.role, "step": request.step, "payload": request.payload},
                        sort_keys=True,
                    ),
                },
            ],
        }

    def wait_seconds(self, delay: float, retry_after: float | None) -> float:
        if retry_after is not None:
            base = min(self.backoff_cap_seconds, max(0.0, retry_after))
        else:
            base = min(self.backoff_cap_seconds, delay)
        jitter = self.rng.random() * (0.25 * base)
        return min(self.backoff_cap_seconds, base + jitter)

    def complete(self, request: CompletionRequest) -> Completion:
        if self.spent_usd >= self.config.max_spend_usd:
            raise ConfigError("refusing live call: MAX_LIVE_SPEND_USD already reached")
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        body = json.dumps(self.build_body(request)).encode("utf-8")
        headers = {
            "Authorization": "Bearer " + self.config.api_key,
            "Content-Type": "application/json",
        }
        delay = self.backoff_base_seconds
        last_transient: TransientProviderError | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                result: HttpResponse | None = self.transport(url, body, headers)
            except TransientProviderError as exc:
                result = None
                last_transient = exc
            if result is not None and result.status == 200:
                completion = self._completion(result.body)
                cost = self._cost(completion.usage)
                if self.spent_usd + cost > self.config.max_spend_usd:
                    raise ConfigError("refusing live call: estimated spend would exceed MAX_LIVE_SPEND_USD")
                self.spent_usd += cost
                self._record(request, completion)
                log_event(
                    _logger(),
                    "live_completed",
                    attempt=attempt,
                    model=self.config.model,
                    spent_usd=self.spent_usd,
                    step=request.key,
                )
                return completion
            retry_after = None if result is None else parse_retry_after(result.headers)
            failed = result is None or result.status in RETRYABLE_STATUS
            if result is not None and not failed:
                raise ProviderError(f"live provider status {result.status}")
            status = None if result is None else result.status
            if attempt >= self.max_attempts:
                log_event(_logger(), "live_retries_exhausted", attempt=attempt, status=status, step=request.key)
                if last_transient is not None and result is None:
                    raise last_transient
                raise TransientProviderError(f"live provider status {status}")
            wait = self.wait_seconds(delay, retry_after)
            self.waits.append(wait)
            log_event(
                _logger(),
                "live_retry",
                attempt=attempt,
                status=status,
                wait_seconds=wait,
                step=request.key,
            )
            self.sleep(wait)
            delay = min(self.backoff_cap_seconds, delay * 2)
        raise TransientProviderError("live provider retries exhausted")

    def _completion(self, body: bytes) -> Completion:
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SchemaError("live response is not JSON") from exc
        content = parse_chat_response(payload)
        usage_raw = payload.get("usage", {}) if isinstance(payload, dict) else {}
        prompt = int(usage_raw.get("prompt_tokens", 0)) if isinstance(usage_raw, dict) else 0
        completion_tokens = int(usage_raw.get("completion_tokens", 0)) if isinstance(usage_raw, dict) else 0
        return Completion(
            content=content,
            usage=Usage(prompt, completion_tokens),
            provider=self.name,
            model=self.config.model,
        )

    def _cost(self, usage: Usage) -> float:
        prompt = (usage.prompt_tokens / 1000.0) * self.config.prompt_usd_per_1k
        completion = (usage.completion_tokens / 1000.0) * self.config.completion_usd_per_1k
        return prompt + completion

    def _record(self, request: CompletionRequest, completion: Completion) -> None:
        if self.cassette_path is None:
            return
        path = self.cassette_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file():
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                loaded = {}
        else:
            loaded = {}
        steps = loaded.get("steps")
        if not isinstance(steps, dict):
            steps = {}
        steps[request.key] = {
            "usage": {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
            },
            "content": completion.content,
        }
        document = {
            "model": self.config.model,
            "notes": (
                "Written by the optional live provider into gitignored var/. "
                "Not a published measurement and not a live result."
            ),
            "price_date": self.config.price_date,
            "steps": steps,
        }
        path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    live_mode: bool = False,
    max_spend_usd: float = 1.0,
    prompt_usd_per_1k: float = 0.0,
    completion_usd_per_1k: float = 0.0,
    price_date: str = "2026-10-17",
) -> CassetteProvider | OpenAICompatProvider:
    if provider == "cassette":
        return CassetteProvider.load(Path(cassette_path))
    if provider in {"openai", "openai-compatible"}:
        if not live_mode and not allow_network:
            raise ConfigError("Live provider is off. Set LIVE_MODE=1 outside CI.")
        if not api_key.strip() or not model.strip() or not base_url.strip():
            raise ConfigError("LLM_API_KEY, LLM_MODEL, and LLM_BASE_URL are required for the live provider")
        config = LiveConfig(
            base_url=base_url,
            model=model,
            api_key=api_key,
            max_spend_usd=max_spend_usd,
            prompt_usd_per_1k=prompt_usd_per_1k,
            completion_usd_per_1k=completion_usd_per_1k,
            price_date=price_date,
        )
        return OpenAICompatProvider(config, live_mode=True)
    raise ConfigError(f"unknown provider {provider}")


def _logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)
