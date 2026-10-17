from __future__ import annotations

import json
import logging
from dataclasses import replace
from io import StringIO

import pytest

from hemp.config import Policy
from hemp.errors import MissingCassetteError, TransientProviderError
from hemp.logging_setup import JsonFormatter, configure_logging, log_event
from hemp.providers.base import CompletionRequest
from hemp.providers.fake import FakeProvider
from hemp.providers.retry import RetryingProvider


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
