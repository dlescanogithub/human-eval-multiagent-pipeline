"""Raw model strings for the live step contract. No network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hemp.cli import _live
from hemp.config import LiveConfig
from hemp.errors import BudgetExhausted, SchemaError
from hemp.providers.base import CompletionRequest
from hemp.providers.llm_openai_compatible import HttpResponse, LlmOpenAICompatible
from hemp.providers.step_schema import (
    CRITIC_EXAMPLE,
    OUTLINE_EXAMPLE,
    VERIFIER_EXAMPLE,
    WRITER_EXAMPLE,
    extract_json_object,
    system_prompt,
    validate_step_content,
)

LESSON_INSTEAD_OF_OUTLINE = {
    "lesson_id": "L1",
    "content": "A Nortia waybill lists the origin dock, the destination dock, and a handoff token.",
    "glossary": ["waybill", "handoff token"],
}
WAYBILL = (
    "A Nortia waybill lists the origin dock, the destination dock, the cargo class, and a four-character handoff token."
)
ONE_LESSON = {
    "id": "L1",
    "title": "Waybills and handoff tokens",
    "objective_ids": ["OBJ-WAYBILL"],
    "prerequisite_ids": [],
    "topics": ["waybill", "handoff token"],
    "body": WAYBILL + " Learners record the token before a shipment leaves the dock.",
    "claims": [{"id": "L1-C1", "text": WAYBILL, "citation_ids": ["F-WAYBILL"]}],
}
ONE_OUTLINE = {
    "course_id": "NL-LOG-101",
    "title": "Foundations of Fictional Logistics",
    "lessons": [
        {
            "id": "L1",
            "title": "Waybills and handoff tokens",
            "objective_ids": ["OBJ-WAYBILL"],
            "prerequisite_ids": [],
        }
    ],
}


class FixedRng:
    def random(self) -> float:
        return 0.0


def _config(**overrides: object) -> LiveConfig:
    raw: dict[str, object] = {
        "base_url": "https://example.invalid/v1",
        "api_key": "local-test-key",
        "model": "fake-model",
        "model_writer": "fake-model",
        "model_verifier": "fake-model",
        "model_critic": "fake-model",
        "max_output_tokens": 32,
        "timeout_s": 5.0,
        "max_spend_usd": 5.0,
        "price_in_per_mtok": 1.0,
        "price_out_per_mtok": 2.0,
        "max_live_tokens": None,
    }
    raw.update(overrides)
    return LiveConfig(
        base_url=str(raw["base_url"]),
        api_key=str(raw["api_key"]),
        model=str(raw["model"]),
        model_writer=str(raw["model_writer"]),
        model_verifier=str(raw["model_verifier"]),
        model_critic=str(raw["model_critic"]),
        max_output_tokens=int(raw["max_output_tokens"]),  # type: ignore[arg-type]
        timeout_s=float(raw["timeout_s"]),  # type: ignore[arg-type]
        max_spend_usd=float(raw["max_spend_usd"]),  # type: ignore[arg-type]
        price_in_per_mtok=None if raw["price_in_per_mtok"] is None else float(raw["price_in_per_mtok"]),  # type: ignore[arg-type]
        price_out_per_mtok=None if raw["price_out_per_mtok"] is None else float(raw["price_out_per_mtok"]),  # type: ignore[arg-type]
        max_live_tokens=None if raw["max_live_tokens"] is None else int(raw["max_live_tokens"]),  # type: ignore[arg-type]
    )


def _envelope(content: str, *, prompt: int = 20, completion: int = 10, cached: int = 0) -> HttpResponse:
    usage: dict[str, object] = {"prompt_tokens": prompt, "completion_tokens": completion}
    if cached:
        usage["prompt_tokens_details"] = {"cached_tokens": cached}
    payload = {"choices": [{"message": {"content": content}}], "usage": usage}
    return HttpResponse(200, {}, json.dumps(payload).encode("utf-8"))


def _provider(config: LiveConfig, transport: object, **kwargs: object) -> LlmOpenAICompatible:
    return LlmOpenAICompatible(
        config,
        transport=transport,  # type: ignore[arg-type]
        sleep=lambda _seconds: None,
        rng=FixedRng(),
        max_schema_retries=int(kwargs.get("max_schema_retries", 2)),  # type: ignore[arg-type]
        ledger_path=kwargs.get("ledger_path"),  # type: ignore[arg-type]
    )


def test_each_step_prompt_names_the_schema() -> None:
    outline = CompletionRequest("writer", "outline", {"course_id": "NL-LOG-101"})
    text = system_prompt(outline)
    assert "STEP: outline" in text
    assert "CALL: outline" in text
    assert "Return ONLY one JSON object" in text
    assert '"lessons"' in text
    assert "Minimal example:" in text
    assert "Do not write the lesson body" in text
    for role, step, marker in (
        ("writer", "draft:L1", "STEP: writer"),
        ("verifier", "L1:r0", "STEP: verifier"),
        ("critic", "L1:r0", "STEP: critic"),
    ):
        rendered = system_prompt(CompletionRequest(role, step, {}))
        assert marker in rendered
        assert "Return ONLY one JSON object" in rendered
        assert "Minimal example:" in rendered
    validate_step_content(outline, OUTLINE_EXAMPLE)
    validate_step_content(CompletionRequest("writer", "draft:L1", {}), WRITER_EXAMPLE)
    validate_step_content(CompletionRequest("verifier", "L1:r0", {}), VERIFIER_EXAMPLE)
    validate_step_content(CompletionRequest("critic", "L1:r0", {}), CRITIC_EXAMPLE)


def test_extracts_fenced_json_and_rejects_missing_fields() -> None:
    fenced = "```json\n" + json.dumps(OUTLINE_EXAMPLE) + "\n```\nThanks."
    assert extract_json_object(fenced)["course_id"] == "NL-LOG-101"
    prose = "Here is the outline:\n" + json.dumps(ONE_OUTLINE) + "\nLet me know."
    assert extract_json_object(prose)["lessons"][0]["id"] == "L1"
    request = CompletionRequest("writer", "draft:L1", {})
    with pytest.raises(SchemaError, match="claims"):
        validate_step_content(
            request,
            {
                "id": "L1",
                "title": "Waybills",
                "body": "text",
                "objective_ids": [],
                "prerequisite_ids": [],
                "topics": [],
            },
        )
    with pytest.raises(SchemaError, match="scores missing safety"):
        broken = json.loads(json.dumps(CRITIC_EXAMPLE))
        del broken["scores"]["safety"]
        validate_step_content(CompletionRequest("critic", "L1:r0", {}), broken)


def test_lesson_instead_of_outline_retries_then_says_why(tmp_path: Path) -> None:
    """Reproduces the live failure: a full lesson where the outline step was required."""
    raw = "I wrote the lesson:\n```json\n" + json.dumps(LESSON_INSTEAD_OF_OUTLINE) + "\n```\nHope that helps.\n"
    bodies: list[bytes] = []

    def transport(url: str, body: bytes, headers: dict[str, str], timeout: float) -> HttpResponse:
        bodies.append(body)
        assert b"STEP: outline" in body
        assert b"Return ONLY one JSON object" in body
        return _envelope(raw)

    provider = _provider(_config(), transport, ledger_path=tmp_path / "spend.jsonl")
    with pytest.raises(SchemaError, match="lessons must be a non-empty list") as caught:
        provider.complete(CompletionRequest("writer", "outline", {"course_id": "NL-LOG-101"}))
    message = str(caught.value)
    assert "looks like a lesson" in message
    assert "validation failed after 2 retries" in message
    assert len(bodies) == 3
    assert b"validation_error" in bodies[1]
    assert b"lessons must be a non-empty list" in bodies[1]


def test_schema_retry_accepts_a_corrected_outline() -> None:
    seen: list[bytes] = []
    answers = [
        _envelope(json.dumps(LESSON_INSTEAD_OF_OUTLINE)),
        _envelope("```json\n" + json.dumps(ONE_OUTLINE) + "\n```"),
    ]

    def transport(url: str, body: bytes, headers: dict[str, str], timeout: float) -> HttpResponse:
        seen.append(body)
        return answers.pop(0)

    provider = _provider(_config(), transport, max_schema_retries=2)
    completion = provider.complete(CompletionRequest("writer", "outline", {}))
    assert completion.content["lessons"][0]["id"] == "L1"
    assert len(seen) == 2
    assert b"validation_error" in seen[1]


def test_schema_retry_stops_when_the_cap_cannot_hold_another_call() -> None:
    calls = {"n": 0}

    def transport(url: str, body: bytes, headers: dict[str, str], timeout: float) -> HttpResponse:
        calls["n"] += 1
        return _envelope(json.dumps(LESSON_INSTEAD_OF_OUTLINE), prompt=1, completion=1)

    config = _config(max_spend_usd=1.0, price_in_per_mtok=0.0, price_out_per_mtok=1_000_000.0, max_output_tokens=1)
    provider = _provider(config, transport, max_schema_retries=2)
    with pytest.raises(BudgetExhausted, match="would exceed"):
        provider.complete(CompletionRequest("writer", "outline", {}))
    assert calls["n"] == 1


def test_cached_prompt_tokens_are_recorded_and_not_discounted(tmp_path: Path) -> None:
    def transport(url: str, body: bytes, headers: dict[str, str], timeout: float) -> HttpResponse:
        return _envelope(json.dumps(OUTLINE_EXAMPLE), prompt=550, completion=10, cached=128)

    ledger = tmp_path / "spend.jsonl"
    provider = _provider(_config(), transport, ledger_path=ledger)
    completion = provider.complete(CompletionRequest("writer", "outline", {}))
    assert completion.usage.cached_tokens == 128
    assert completion.usage.prompt_tokens == 550
    row = json.loads(ledger.read_text(encoding="utf-8"))
    assert row["cached_tokens"] == 128
    assert row["cost"] == pytest.approx((550 / 1_000_000) * 1.0 + (10 / 1_000_000) * 2.0)
    assert "overestimate" in row["cost_note"]


def test_live_runs_one_piece_on_raw_step_responses(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    steps: list[str] = []

    def transport(url: str, body: bytes, headers: dict[str, str], timeout: float) -> HttpResponse:
        payload = json.loads(body.decode("utf-8"))
        system = str(payload["messages"][0]["content"])
        assert "Return ONLY one JSON object" in system
        if "STEP: outline" in system:
            content: object = ONE_OUTLINE
        elif "STEP: writer" in system:
            content = ONE_LESSON
        elif "STEP: verifier" in system:
            content = VERIFIER_EXAMPLE
        elif "STEP: critic" in system:
            content = CRITIC_EXAMPLE
        else:
            raise AssertionError(system.split("\n", 1)[0])
        steps.append(system.split("\n", 1)[0])
        return _envelope(json.dumps(content))

    monkeypatch.setenv("LIVE_LLM", "1")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("LLM_MODEL", "fake-model")
    monkeypatch.setenv("LLM_API_KEY", "local-test-key")
    monkeypatch.setenv("MAX_LIVE_SPEND_USD", "5")
    monkeypatch.setenv("LLM_PRICE_IN_PER_MTOK", "1")
    monkeypatch.setenv("LLM_PRICE_OUT_PER_MTOK", "2")

    def factory(root: Path, config: LiveConfig) -> LlmOpenAICompatible:
        return _provider(config, transport)

    assert _live(repo_root, pieces=1, provider_factory=factory) == 0
    finished = json.loads(capsys.readouterr().out)
    assert finished["live_result_claimed"] is False
    assert finished["published"] == 0
    assert finished["pending"] == 1
    assert steps == ["STEP: outline", "STEP: writer", "STEP: verifier", "STEP: critic"]


def test_cli_reports_the_outline_mismatch(
    repo_root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def transport(url: str, body: bytes, headers: dict[str, str], timeout: float) -> HttpResponse:
        raw = "```json\n" + json.dumps(LESSON_INSTEAD_OF_OUTLINE) + "\n```"
        return _envelope(raw)

    monkeypatch.setenv("LIVE_LLM", "1")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("LLM_MODEL", "fake-model")
    monkeypatch.setenv("LLM_API_KEY", "local-test-key")
    monkeypatch.setenv("MAX_LIVE_SPEND_USD", "5")
    monkeypatch.setenv("LLM_PRICE_IN_PER_MTOK", "1")
    monkeypatch.setenv("LLM_PRICE_OUT_PER_MTOK", "2")

    def factory(root: Path, config: LiveConfig) -> LlmOpenAICompatible:
        return _provider(config, transport, max_schema_retries=1)

    assert _live(repo_root, pieces=1, provider_factory=factory) == 2
    failed = json.loads(capsys.readouterr().out)
    assert failed["exit_code"] == 2
    assert "lessons must be a non-empty list" in failed["error"]
    assert "looks like a lesson" in failed["error"]
    assert "local-test-key" not in failed["error"]
