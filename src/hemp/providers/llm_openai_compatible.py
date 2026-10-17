"""Optional live provider: OpenAI-compatible chat-completions over HTTP.

Off unless ``LIVE_LLM=1``. Tests inject a transport and never open a socket.
Prices are read from the environment at run time. This module stores none.
"""

from __future__ import annotations

import json
import logging
import random
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Protocol

from hemp.config import LiveConfig
from hemp.errors import BudgetExhausted, ConfigError, ProviderError, SchemaError, TransientProviderError
from hemp.logging_setup import log_event
from hemp.models import Usage
from hemp.providers.base import Completion, CompletionRequest
from hemp.providers.step_schema import extract_json_object, system_prompt, validate_step_content

LOGGER_NAME = "hemp.live"
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
AUTH_STATUS = {401, 403}
DATA_OPEN = "<untrusted-data>"
DATA_CLOSE = "</untrusted-data>"


class Rng(Protocol):
    def random(self) -> float:
        """Return a float in [0.0, 1.0)."""


class Sleeper(Protocol):
    def __call__(self, seconds: float) -> None:
        """Pause. Tests pass a recorder."""


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: dict[str, str]
    body: bytes


class Transport(Protocol):
    def __call__(self, url: str, body: bytes, headers: Mapping[str, str], timeout: float) -> HttpResponse:
        """One HTTP POST. The default implementation is not used in tests or CI."""


def redact(text: str, secret: str) -> str:
    if not secret or secret not in text:
        return text
    return text.replace(secret, "[REDACTED]")


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
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    current = datetime.now(UTC).timestamp() if now_epoch is None else now_epoch
    return max(0.0, parsed.timestamp() - current)


def urllib_transport(  # pragma: no cover
    url: str,
    body: bytes,
    headers: Mapping[str, str],
    timeout: float,
) -> HttpResponse:
    request = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")  # pragma: no cover
    try:  # pragma: no cover
        with urllib.request.urlopen(request, timeout=timeout) as response:  # pragma: no cover
            return HttpResponse(response.status, dict(response.headers), response.read())  # pragma: no cover
    except urllib.error.HTTPError as exc:  # pragma: no cover
        payload = exc.read()  # pragma: no cover
        return HttpResponse(exc.code, dict(exc.headers), payload)  # pragma: no cover
    except (urllib.error.URLError, TimeoutError) as exc:  # pragma: no cover
        raise TransientProviderError("live transport failed") from exc  # pragma: no cover


def delimit_data(label: str, payload: object) -> str:
    rendered = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return f'{DATA_OPEN} source="{label}"\n{rendered}\n{DATA_CLOSE}'


def build_messages(request: CompletionRequest, *, validation_feedback: str | None = None) -> list[dict[str, str]]:
    """Corpus text and prior role output travel as delimited data, not as instructions."""
    data = request.payload.get("untrusted_data", {})
    blocks = [
        delimit_data("corpus", data.get("corpus", [])),
        delimit_data("prior_output", data.get("prior_output")),
        delimit_data("task", {key: value for key, value in request.payload.items() if key != "untrusted_data"}),
    ]
    if validation_feedback:
        blocks.append(delimit_data("validation_error", {"error": validation_feedback}))
    return [
        {"role": "system", "content": system_prompt(request)},
        {"role": "user", "content": "\n".join(blocks)},
    ]


def validate_citation_ids(content: object, corpus_ids: set[str]) -> None:
    """Every cited id must exist. An empty list is left for the checker to reject."""

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key in ("citation_ids", "corpus_ids"):
                if key not in node:
                    continue
                cited = node[key]
                if not isinstance(cited, list) or not all(isinstance(item, str) for item in cited):
                    raise SchemaError(f"{key} must be a list of strings")
                unknown = [item for item in cited if item not in corpus_ids]
                if unknown:
                    raise SchemaError("citation ids not in the corpus: " + ",".join(unknown))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(content)


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
    return extract_json_object(content)


@dataclass
class Budget:
    """Reserve the worst case before a call, then replace it with reported usage."""

    max_spend_usd: float
    price_in_per_mtok: float | None
    price_out_per_mtok: float | None
    max_live_tokens: int | None
    max_output_tokens: int
    spent_usd: float = 0.0
    spent_tokens: int = 0
    held_usd: float = 0.0
    held_tokens: int = 0
    holds: list[tuple[float, int]] = field(default_factory=list)

    @property
    def prices_known(self) -> bool:
        return self.price_in_per_mtok is not None and self.price_out_per_mtok is not None

    def estimate_input_tokens(self, body: bytes) -> int:
        return max(1, len(body) // 4)

    def _worst_usd(self, input_tokens: int, output_tokens: int) -> float:
        assert self.price_in_per_mtok is not None and self.price_out_per_mtok is not None
        incoming = (input_tokens / 1_000_000) * self.price_in_per_mtok
        outgoing = (output_tokens / 1_000_000) * self.price_out_per_mtok
        return incoming + outgoing

    def reserve(self, input_tokens: int, output_tokens: int) -> None:
        if self.prices_known:
            worst = self._worst_usd(input_tokens, output_tokens)
            if self.spent_usd + self.held_usd + worst > self.max_spend_usd:
                raise BudgetExhausted("refusing live call: worst-case cost would exceed MAX_LIVE_SPEND_USD")
            self.held_usd += worst
            self.holds.append((worst, 0))
            return
        if self.max_live_tokens is None:
            raise ConfigError("MAX_LIVE_TOKENS is required when live prices are unset")
        worst_tokens = input_tokens + output_tokens
        if self.spent_tokens + self.held_tokens + worst_tokens > self.max_live_tokens:
            raise BudgetExhausted("refusing live call: worst-case tokens would exceed MAX_LIVE_TOKENS")
        self.held_tokens += worst_tokens
        self.holds.append((0.0, worst_tokens))

    def reconcile(self, input_tokens: int, output_tokens: int) -> float | str:
        if not self.holds:
            raise ConfigError("reconcile called without a reservation")
        held_usd, held_tokens = self.holds.pop()
        self.held_usd -= held_usd
        self.held_tokens -= held_tokens
        self.spent_tokens += input_tokens + output_tokens
        if not self.prices_known:
            if self.max_live_tokens is not None and self.spent_tokens > self.max_live_tokens:
                raise BudgetExhausted("live token cap reached after reconciling usage", cost="unknown")
            return "unknown"
        actual = self._worst_usd(input_tokens, output_tokens)
        self.spent_usd += actual
        if self.spent_usd > self.max_spend_usd:
            raise BudgetExhausted("live spend cap reached after reconciling usage", cost=actual)
        return actual


class LlmOpenAICompatible:
    """Chat-completions client. One model per role. Budget is checked before the socket."""

    name = "llm_openai_compatible"

    def __init__(
        self,
        config: LiveConfig,
        *,
        transport: Transport | None = None,
        sleep: Sleeper | None = None,
        rng: Rng | None = None,
        max_attempts: int = 3,
        backoff_base_seconds: float = 0.5,
        backoff_cap_seconds: float = 8.0,
        ledger_path: Path | None = None,
        max_schema_retries: int = 2,
    ) -> None:
        if max_attempts < 1:
            raise ConfigError("max_attempts must be at least 1")
        if max_schema_retries < 0 or max_schema_retries > 2:
            raise ConfigError("max_schema_retries must be from 0 to 2")
        self.config = config
        self.transport = transport or urllib_transport
        self.sleep = sleep or (lambda _seconds: None)
        self.rng = rng or random.Random()
        self.max_attempts = max_attempts
        self.backoff_base_seconds = backoff_base_seconds
        self.backoff_cap_seconds = backoff_cap_seconds
        self.ledger_path = ledger_path
        self.max_schema_retries = max_schema_retries
        self.budget = Budget(
            max_spend_usd=config.max_spend_usd,
            price_in_per_mtok=config.price_in_per_mtok,
            price_out_per_mtok=config.price_out_per_mtok,
            max_live_tokens=config.max_live_tokens,
            max_output_tokens=config.max_output_tokens,
        )
        self.waits: list[float] = []

    def build_body(self, request: CompletionRequest, *, validation_feedback: str | None = None) -> dict[str, Any]:
        return {
            "model": self.config.model_for(request.role),
            "temperature": 0,
            "max_tokens": self.config.max_output_tokens,
            "response_format": {"type": "json_object"},
            "messages": build_messages(request, validation_feedback=validation_feedback),
        }

    def wait_seconds(self, delay: float, retry_after: float | None) -> float:
        if retry_after is not None:
            base = min(self.backoff_cap_seconds, max(0.0, retry_after))
        else:
            base = min(self.backoff_cap_seconds, delay)
        jitter = self.rng.random() * (0.25 * base)
        return min(self.backoff_cap_seconds, base + jitter)

    def complete(self, request: CompletionRequest) -> Completion:
        feedback: str | None = None
        schema_failures = 0
        while True:
            try:
                completion = self._call_once(request, feedback)
            except SchemaError as exc:
                if schema_failures >= self.max_schema_retries:
                    raise SchemaError(f"validation failed after {schema_failures} retries. {exc}") from None
                schema_failures += 1
                feedback = str(exc)
                continue
            return completion

    def _call_once(self, request: CompletionRequest, feedback: str | None) -> Completion:
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        body = json.dumps(self.build_body(request, validation_feedback=feedback)).encode("utf-8")
        headers = {
            "Authorization": "Bearer " + self.config.api_key,
            "Content-Type": "application/json",
        }
        estimated_in = self.budget.estimate_input_tokens(body)
        self.budget.reserve(estimated_in, self.config.max_output_tokens)
        try:
            return self._attempt(request, url, body, headers)
        except BudgetExhausted:
            raise
        except SchemaError:
            raise
        except Exception:
            self._release_hold()
            raise

    def _release_hold(self) -> None:
        if not self.budget.holds:
            return
        held_usd, held_tokens = self.budget.holds.pop()
        self.budget.held_usd -= held_usd
        self.budget.held_tokens -= held_tokens

    def _attempt(self, request: CompletionRequest, url: str, body: bytes, headers: dict[str, str]) -> Completion:
        delay = self.backoff_base_seconds
        last_transient: TransientProviderError | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                result: HttpResponse | None = self.transport(url, body, headers, self.config.timeout_s)
            except TransientProviderError as exc:
                result = None
                last_transient = TransientProviderError(redact(str(exc), self.config.api_key))
            except Exception as exc:
                raise ProviderError(redact(str(exc), self.config.api_key)) from None
            if result is not None and result.status == 200:
                return self._accept(request, result.body)
            if result is not None and result.status in AUTH_STATUS:
                raise ProviderError(f"live provider auth status {result.status}")
            failed = result is None or result.status in RETRYABLE_STATUS
            if result is not None and not failed:
                raise ProviderError(f"live provider status {result.status}")
            status = None if result is None else result.status
            if attempt >= self.max_attempts:
                log_event(
                    _logger(),
                    "live_retries_exhausted",
                    attempt=attempt,
                    status=status,
                    step=request.key,
                    model=self.config.model_for(request.role),
                )
                if last_transient is not None and result is None:
                    raise last_transient
                raise TransientProviderError(f"live provider status {status}")
            retry_after = None if result is None else parse_retry_after(result.headers)
            wait = self.wait_seconds(delay, retry_after)
            self.waits.append(wait)
            log_event(
                _logger(),
                "live_retry",
                attempt=attempt,
                status=status,
                wait_seconds=wait,
                step=request.key,
                model=self.config.model_for(request.role),
            )
            self.sleep(wait)
            delay = min(self.backoff_cap_seconds, delay * 2)
        raise TransientProviderError("live provider retries exhausted")

    def _accept(self, request: CompletionRequest, body: bytes) -> Completion:
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._release_hold()
            raise SchemaError(
                "live response is not a JSON chat completion. message.content must be one JSON object for this step."
            ) from None
        usage_raw = payload.get("usage", {}) if isinstance(payload, dict) else {}
        prompt, completion_tokens, cached = _usage_counts(usage_raw)
        schema_error: SchemaError | None = None
        try:
            content = parse_chat_response(payload)
            corpus_ids = _corpus_ids(request)
            if corpus_ids:
                validate_citation_ids(content, corpus_ids)
            validate_step_content(request, content)
        except SchemaError as exc:
            content = {}
            schema_error = exc
        completion = Completion(
            content=content,
            usage=Usage(prompt, completion_tokens, cached),
            provider=self.name,
            model=self.config.model_for(request.role),
        )
        try:
            cost = self.budget.reconcile(prompt, completion_tokens)
        except BudgetExhausted as exc:
            recorded: float | str = "unknown" if exc.cost is None else exc.cost
            self._ledger(request, completion, recorded, cached)
            raise
        self._ledger(request, completion, cost, cached)
        if schema_error is not None:
            raise schema_error
        log_event(
            _logger(),
            "live_completed",
            step=request.key,
            model=completion.model,
            tokens_in=prompt,
            tokens_out=completion_tokens,
            cached_tokens=cached,
            cost=cost,
        )
        return completion

    def _ledger(
        self,
        request: CompletionRequest,
        completion: Completion,
        cost: float | str,
        cached_tokens: int = 0,
    ) -> None:
        if self.ledger_path is None:
            return
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts": datetime.now(UTC).isoformat(),
            "role": request.role,
            "model": completion.model,
            "tokens_in": completion.usage.prompt_tokens,
            "tokens_out": completion.usage.completion_tokens,
            "cached_tokens": cached_tokens,
            "cost": cost,
            "cost_note": (
                "input price applied to every prompt token; cached tokens, when reported, make this an overestimate"
            ),
        }
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _usage_counts(usage_raw: object) -> tuple[int, int, int]:
    if not isinstance(usage_raw, dict):
        return 0, 0, 0
    prompt = _as_int(usage_raw.get("prompt_tokens"))
    completion = _as_int(usage_raw.get("completion_tokens"))
    cached = _as_int(usage_raw.get("cached_tokens"))
    details = usage_raw.get("prompt_tokens_details")
    if isinstance(details, dict):
        cached = max(cached, _as_int(details.get("cached_tokens")))
    return prompt, completion, cached


def _as_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value)


def _corpus_ids(request: CompletionRequest) -> set[str]:
    data = request.payload.get("untrusted_data", {})
    corpus = data.get("corpus", []) if isinstance(data, dict) else []
    if not isinstance(corpus, list):
        return set()
    ids: set[str] = set()
    for item in corpus:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            ids.add(item["id"])
    return ids


def _logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)
