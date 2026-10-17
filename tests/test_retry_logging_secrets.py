from __future__ import annotations

import json
import logging
from dataclasses import replace
from io import StringIO
from pathlib import Path

import pytest

from hemp.config import Policy
from hemp.errors import MissingCassetteError, TransientProviderError
from hemp.logging_setup import JsonFormatter, configure_logging, log_event
from hemp.providers.base import CompletionRequest
from hemp.providers.fake import FakeProvider
from hemp.providers.retry import RetryingProvider
from hemp.secretscan import file_sha256, scan


def test_retries_then_succeeds_and_caps_backoff() -> None:
    delays: list[float] = []
    provider = FakeProvider({"writer:outline": {"ok": True}}, fail_times={"writer:outline": 2})
    policy = replace(Policy(), backoff_base_seconds=1.5, backoff_cap_seconds=2.0, max_attempts=3)
    wrapped = RetryingProvider(provider, policy, sleep=delays.append)
    completion = wrapped.complete(CompletionRequest("writer", "outline", {}))
    assert completion.content == {"ok": True}
    assert delays == [1.5, 2.0]
    assert wrapped.attempts == ["writer:outline#1", "writer:outline#2", "writer:outline#3"]


def test_retries_exhausted() -> None:
    provider = FakeProvider({}, fail_times={"writer:draft:L1": 5})
    wrapped = RetryingProvider(FakeProvider({}, fail_times={"writer:draft:L1": 5}), Policy())
    with pytest.raises(TransientProviderError):
        wrapped.complete(CompletionRequest("writer", "draft:L1", {}))
    assert len(wrapped.attempts) == 3
    assert provider.calls == []


def test_missing_cassette_is_not_retried() -> None:
    wrapped = RetryingProvider(FakeProvider({}), Policy())
    with pytest.raises(MissingCassetteError):
        wrapped.complete(CompletionRequest("writer", "outline", {}))
    assert wrapped.attempts == ["writer:outline#1"]


def test_json_log_line() -> None:
    stream = StringIO()
    logger = configure_logging("INFO", stream)
    log_event(logger, "course_generated", course_id="NL-LOG-101")
    payload = json.loads(stream.getvalue())
    assert payload["message"] == "course_generated"
    assert payload["fields"]["course_id"] == "NL-LOG-101"
    assert payload["level"] == "INFO"


def test_formatter_includes_exception() -> None:
    formatter = JsonFormatter()
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        record = logging.LogRecord("hemp", logging.ERROR, __file__, 1, "failed", (), None)
        record.exc_info = (RuntimeError, RuntimeError("boom"), None)
        rendered = formatter.format(record)
    assert "boom" in rendered


def _join(*parts: str) -> str:
    return "".join(parts)


def test_secretscan_finds_planted_key_and_repo_is_clean(repo_root: Path, tmp_path: Path) -> None:
    bad = tmp_path / "notes.txt"
    bad.write_text("token = '" + _join("s", "k-") + ("a" * 24) + "'\n", encoding="utf-8")
    found = scan(tmp_path)
    assert found and found[0].rule == "openai_key"
    assert scan(repo_root) == []


def test_secretscan_positive_shapes(tmp_path: Path) -> None:
    samples = [
        ("xai_key", _join("xa", "i-") + ("a" * 20)),
        ("openai_key", _join("s", "k-") + ("b" * 20)),
        ("openai_key", _join("s", "k-", "proj-") + ("c" * 20)),
        ("anthropic_key", _join("s", "k-", "ant-") + ("d" * 20)),
        ("elevenlabs_key", _join("s", "k_") + ("e" * 20)),
        ("github_token", _join("gh", "p_") + ("f" * 20)),
        ("github_token", _join("github", "_pat_") + ("g" * 20)),
        ("aws_access_key", _join("AK", "IA") + ("H" * 16)),
        ("bearer_token", _join("Bea", "rer ") + ("i" * 20)),
        ("private_key", _join("-----BEGIN ", "PRIVATE KEY-----")),
        ("private_key", _join("-----BEGIN ", "RSA PRIVATE KEY-----")),
        ("private_key", _join("-----BEGIN ", "OPENSSH PRIVATE KEY-----")),
        ("private_key", _join("-----BEGIN ", "EC PRIVATE KEY-----")),
    ]
    for index, (rule, secret) in enumerate(samples):
        folder = tmp_path / f"case-{index}"
        folder.mkdir()
        (folder / "note.txt").write_text(secret + "\n", encoding="utf-8")
        found = scan(folder)
        assert len(found) == 1
        assert found[0].rule == rule


def test_secretscan_negative_shapes(tmp_path: Path) -> None:
    lines = [
        _join("s", "k-") + ("a" * 19),
        _join("xa", "i-") + ("a" * 19),
        _join("s", "k-", "ant-") + ("d" * 19),
        _join(
            "s",
            "k_",
        )
        + ("e" * 19),
        _join("gh", "p_") + ("f" * 19),
        _join("github", "_pat_") + ("g" * 19),
        _join("AK", "IA") + ("H" * 15),
        _join("Bea", "rer ") + ("i" * 19),
        _join("-----BEGIN ", "PUBLIC KEY-----"),
        'API_KEY="changeme"',
        "a token is mentioned but not assigned",
    ]
    (tmp_path / "clean.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert scan(tmp_path) == []


def test_secretscan_sha256_matches_provenance(repo_root: Path) -> None:
    digest = file_sha256(repo_root / "src" / "hemp" / "secretscan.py")
    text = (repo_root / "docs" / "PROVENANCE.md").read_text(encoding="utf-8")
    assert f"src/hemp/secretscan.py sha256 {digest}" in text


def test_secretscan_ignores_placeholder(tmp_path: Path) -> None:
    sample = tmp_path / "example.env"
    sample.write_text('API_KEY="changeme"\n', encoding="utf-8")
    assert scan(tmp_path) == []
