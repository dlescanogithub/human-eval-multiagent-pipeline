from __future__ import annotations

import json
from pathlib import Path

import pytest

from hemp.cli import _live, default_live_provider
from hemp.config import LiveConfig, load_live_config
from hemp.errors import ConfigError, ProviderError, TransientProviderError
from hemp.logging_setup import configure_logging
from hemp.providers.base import CompletionRequest
from hemp.providers.cassette import CassetteProvider
from hemp.providers.fake import FakeProvider
from hemp.providers.openai_compat import (
    HttpResponse,
    OpenAICompatProvider,
    parse_retry_after,
)

NOW = 1_760_000_000.0


class FixedRng:
    def __init__(self, value: float) -> None:
        self.value = value

    def random(self) -> float:
        return self.value


def _config(**overrides: float | str) -> LiveConfig:
    raw: dict[str, float | str] = {
        "base_url": "https://example.invalid/v1",
        "model": "fake-model",
        "api_key": "local-test-key",
        "max_spend_usd": 5.0,
        "prompt_usd_per_1k": 0.01,
        "completion_usd_per_1k": 0.02,
        "price_date": "2026-10-17",
    }
    raw.update(overrides)
    return LiveConfig(
        base_url=str(raw["base_url"]),
        model=str(raw["model"]),
        api_key=str(raw["api_key"]),
        max_spend_usd=float(raw["max_spend_usd"]),
        prompt_usd_per_1k=float(raw["prompt_usd_per_1k"]),
        completion_usd_per_1k=float(raw["completion_usd_per_1k"]),
        price_date=str(raw["price_date"]),
    )


def _ok(prompt: int = 100, completion: int = 50, content: dict[str, object] | None = None) -> HttpResponse:
    payload = {
        "choices": [{"message": {"content": json.dumps(content or {"ok": True})}}],
        "usage": {"prompt_tokens": prompt, "completion_tokens": completion},
    }
    return HttpResponse(200, {}, json.dumps(payload).encode("utf-8"))


def _env() -> dict[str, str]:
    return {
        "LIVE_MODE": "1",
        "LLM_BASE_URL": "https://example.invalid/v1",
        "LLM_MODEL": "fake-model",
        "LLM_API_KEY": "local-test-key",
        "MAX_LIVE_SPEND_USD": "2",
        "LLM_PROMPT_USD_PER_1K": "0.01",
        "LLM_COMPLETION_USD_PER_1K": "0.02",
        "LLM_PRICE_DATE": "2026-10-17",
    }


def test_live_config_closed_failures() -> None:
    with pytest.raises(ConfigError, match="LIVE_MODE"):
        load_live_config({})
    with pytest.raises(ConfigError, match="missing"):
        load_live_config({"LIVE_MODE": "1"})
    broken = _env()
    broken["MAX_LIVE_SPEND_USD"] = "0"
    with pytest.raises(ConfigError, match="positive"):
        load_live_config(broken)
    broken = _env()
    broken["LLM_PRICE_DATE"] = "October"
    with pytest.raises(ConfigError, match="YYYY-MM-DD"):
        load_live_config(broken)
    broken = _env()
    broken["LLM_PROMPT_USD_PER_1K"] = "nope"
    with pytest.raises(ConfigError, match="numbers"):
        load_live_config(broken)
    loaded = load_live_config(_env())
    assert loaded.model == "fake-model"
    assert loaded.max_spend_usd == 2.0


def test_retry_after_and_jitter(tmp_path: Path) -> None:
    seen: list[HttpResponse] = [
        HttpResponse(429, {"Retry-After": "1.5"}, b""),
        _ok(),
    ]

    def transport(url: str, body: bytes, headers: dict[str, str]) -> HttpResponse:
        assert headers["Authorization"] == "Bearer local-test-key"
        assert url.endswith("/chat/completions")
        assert b"local-test-key" not in body
        return seen.pop(0)

    waits: list[float] = []
    provider = OpenAICompatProvider(
        _config(),
        live_mode=True,
        transport=transport,
        sleep=waits.append,
        rng=FixedRng(0.0),
        cassette_path=tmp_path / "cassette.json",
    )
    completion = provider.complete(CompletionRequest("writer", "outline", {"lesson": "L1"}))
    assert completion.content == {"ok": True}
    assert waits == [1.5]
    stored = CassetteProvider.load(tmp_path / "cassette.json")
    assert "writer:outline" in stored.steps
    assert "local-test-key" not in (tmp_path / "cassette.json").read_text(encoding="utf-8")

    jittered: list[HttpResponse] = [HttpResponse(503, {}, b""), _ok()]

    def transport_503(url: str, body: bytes, headers: dict[str, str]) -> HttpResponse:
        return jittered.pop(0)

    waits.clear()
    provider = OpenAICompatProvider(
        _config(),
        live_mode=True,
        transport=transport_503,
        sleep=waits.append,
        rng=FixedRng(1.0),
        backoff_base_seconds=0.5,
        backoff_cap_seconds=8.0,
    )
    provider.complete(CompletionRequest("writer", "draft:L1", {}))
    assert waits == [pytest.approx(0.625)]


def test_retries_exhausted_and_permanent_status() -> None:
    def always_503(url: str, body: bytes, headers: dict[str, str]) -> HttpResponse:
        return HttpResponse(503, {}, b"")

    waits: list[float] = []
    provider = OpenAICompatProvider(
        _config(),
        live_mode=True,
        transport=always_503,
        sleep=waits.append,
        rng=FixedRng(0.0),
        backoff_base_seconds=0.5,
    )
    with pytest.raises(TransientProviderError):
        provider.complete(CompletionRequest("writer", "outline", {}))
    assert waits == [0.5, 1.0]

    def denied(url: str, body: bytes, headers: dict[str, str]) -> HttpResponse:
        return HttpResponse(400, {}, b"")

    waits.clear()
    provider = OpenAICompatProvider(_config(), live_mode=True, transport=denied, sleep=waits.append, rng=FixedRng(0.0))
    with pytest.raises(ProviderError):
        provider.complete(CompletionRequest("writer", "outline", {}))
    assert waits == []


def test_spend_cap_and_transport_failure(tmp_path: Path) -> None:
    calls = {"n": 0}

    def transport(url: str, body: bytes, headers: dict[str, str]) -> HttpResponse:
        calls["n"] += 1
        return _ok(prompt=1000, completion=0)

    provider = OpenAICompatProvider(
        _config(max_spend_usd=1.0, prompt_usd_per_1k=1.0, completion_usd_per_1k=0.0),
        live_mode=True,
        transport=transport,
        rng=FixedRng(0.0),
        cassette_path=tmp_path / "cassette.json",
    )
    provider.complete(CompletionRequest("writer", "outline", {}))
    with pytest.raises(ConfigError, match="already reached"):
        provider.complete(CompletionRequest("critic", "review:L1", {}))
    assert calls["n"] == 1

    def expensive(url: str, body: bytes, headers: dict[str, str]) -> HttpResponse:
        return _ok(prompt=5000, completion=0)

    provider = OpenAICompatProvider(
        _config(max_spend_usd=1.0, prompt_usd_per_1k=1.0, completion_usd_per_1k=0.0),
        live_mode=True,
        transport=expensive,
        rng=FixedRng(0.0),
        cassette_path=tmp_path / "over.json",
    )
    with pytest.raises(ConfigError, match="would exceed"):
        provider.complete(CompletionRequest("writer", "outline", {}))
    assert not (tmp_path / "over.json").exists()

    state = {"failed": True}

    def flaky(url: str, body: bytes, headers: dict[str, str]) -> HttpResponse:
        if state["failed"]:
            state["failed"] = False
            raise TransientProviderError("timeout")
        return _ok()

    waits: list[float] = []
    provider = OpenAICompatProvider(_config(), live_mode=True, transport=flaky, sleep=waits.append, rng=FixedRng(0.0))
    assert provider.complete(CompletionRequest("writer", "outline", {})).content == {"ok": True}
    assert waits == [0.5]


def test_logs_omit_the_key() -> None:
    from io import StringIO

    stream = StringIO()
    configure_logging("INFO", stream)

    def transport(url: str, body: bytes, headers: dict[str, str]) -> HttpResponse:
        return HttpResponse(429, {"Retry-After": "0"}, b"")

    key = "local-test-key"
    provider = OpenAICompatProvider(
        _config(api_key=key),
        live_mode=True,
        transport=transport,
        sleep=lambda _seconds: None,
        rng=FixedRng(0.0),
        max_attempts=1,
    )
    with pytest.raises(TransientProviderError):
        provider.complete(CompletionRequest("writer", "outline", {}))
    rendered = stream.getvalue()
    assert key not in rendered
    assert "live_retries_exhausted" in rendered


def test_retry_after_http_date() -> None:
    headers = {"retry-after": "Sat, 17 Oct 2026 12:00:02 GMT"}
    moment = 1792238400.0  # 2026-10-17 12:00:00 UTC
    assert parse_retry_after(headers, now_epoch=moment) == pytest.approx(2.0)
    assert parse_retry_after({}, now_epoch=moment) is None
    assert parse_retry_after({"Retry-After": "not-a-date"}, now_epoch=moment) is None
    assert parse_retry_after({"Retry-After": "-4"}, now_epoch=moment) == 0.0


def test_cli_live_refuses_and_runs_only_with_an_injected_provider(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("LIVE_MODE", raising=False)
    assert _live(repo_root) == 2
    refused = json.loads(capsys.readouterr().out)
    assert refused["exit_code"] == 2
    assert refused["event"] == "live_refused"

    for name, value in _env().items():
        monkeypatch.setenv(name, value)

    def factory(root: Path, config: LiveConfig) -> CassetteProvider:
        assert config.price_date == "2026-10-17"
        return CassetteProvider.load(repo_root / "fixtures" / "cassettes" / "happy.json")

    assert _live(repo_root, factory) == 0
    finished = json.loads(capsys.readouterr().out)
    assert finished["live_result_claimed"] is False
    assert finished["published"] == 0
    assert finished["pending"] == 4

    def broken(root: Path, config: LiveConfig) -> FakeProvider:
        return FakeProvider({})

    assert _live(repo_root, broken) == 2
    failed = json.loads(capsys.readouterr().out)
    assert failed["event"] == "live_failed"
    assert failed["exit_code"] == 2

    built = default_live_provider(repo_root, _config())
    assert built.name == "openai-compatible"
    assert built.cassette_path == repo_root / "var" / "live" / "cassette.json"
    assert not built.cassette_path.exists() or built.cassette_path.parent.is_dir()
