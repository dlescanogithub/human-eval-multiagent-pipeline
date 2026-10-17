from __future__ import annotations

import json
from pathlib import Path

import pytest

from hemp.cli import main
from hemp.config import LiveConfig, find_root, load_settings
from hemp.errors import ConfigError, SchemaError
from hemp.evalkit.runner import EXIT_GATE_RED, EXIT_OK, default_cases, run_case
from hemp.load import load_course, read_json
from hemp.providers import build_provider, parse_chat_response
from hemp.providers.base import CompletionRequest
from hemp.providers.llm_openai_compatible import LlmOpenAICompatible
from hemp.review.server import ReviewApp, render_queue, serve
from hemp.secretscan import scan_repo


def test_happy_gate_and_regression(repo_root: Path) -> None:
    happy, repeat, uncited, poison = default_cases(repo_root)
    happy_report = run_case(happy)
    assert happy_report.quality_passed
    assert happy_report.safety_passed
    assert happy_report.metrics["published"] == 4
    assert happy_report.metrics["writer_calls"]["L2"] == 2
    assert happy_report.metrics["approval_basis"] == "synthetic"
    assert happy_report.metrics["cohens_kappa_rater1_rater2"] == 1.0
    assert happy_report.metrics["cohens_kappa_clarity"] == pytest.approx(0.5)

    repeat_report = run_case(repeat)
    assert not repeat_report.quality_passed
    assert repeat_report.safety_passed
    assert "redundancy" in repeat_report.blocking_codes
    assert repeat_report.metrics["published"] == 1

    uncited_report = run_case(uncited)
    assert not uncited_report.quality_passed
    assert uncited_report.safety_passed
    assert "uncited_claim" in uncited_report.blocking_codes
    assert uncited_report.metrics["published"] == 0

    poison_report = run_case(poison)
    assert not poison_report.quality_passed
    assert poison_report.safety_passed
    assert "uncited_claim" in poison_report.blocking_codes
    assert poison_report.metrics["published"] == 0
    assert poison_report.metrics["provider"] == "fake"


def test_cli_eval_demo_generate_and_review(repo_root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--root", str(repo_root), "eval"]) == EXIT_OK
    eval_out = capsys.readouterr().out
    assert "EVAL_PASS" in eval_out
    assert main(["--root", str(repo_root), "eval-regression"]) == EXIT_GATE_RED
    assert "GATE_RED" in capsys.readouterr().out

    demo_dir = tmp_path / "demo"
    assert main(["--root", str(repo_root), "demo", "--artifact-dir", str(demo_dir)]) == 0
    demo_text = capsys.readouterr().out
    assert "100% synthetic" in demo_text
    assert "COMPUTATION DEMO" in demo_text
    assert "not a human study" in demo_text
    assert "n_items=48" in demo_text
    report = json.loads((demo_dir / "report.json").read_text(encoding="utf-8"))
    assert report["published"] == 4
    assert (demo_dir / "trace.jsonl").read_text(encoding="utf-8").count("rubric_version") > 0

    pending_dir = tmp_path / "pending"
    assert main(["--root", str(repo_root), "generate", "--artifact-dir", str(pending_dir)]) == 0
    pending = json.loads((pending_dir / "queue.json").read_text(encoding="utf-8"))
    assert pending["items"]
    assert all(item["status"] == "pending" for item in pending["items"])
    assert all(item["labels"] == [] for item in pending["items"])

    queue_path = pending_dir / "queue.json"
    assert main(["review", "list", "--queue", str(queue_path)]) == 0
    piece = pending["items"][0]["piece_id"]
    assert (
        main(
            [
                "review",
                "decide",
                "--queue",
                str(queue_path),
                "--piece",
                piece,
                "--rater",
                "local-owner",
                "--scores",
                "accuracy=5,clarity=5,flow=5,no_redundancy=5,safety=5",
            ]
        )
        == 0
    )
    updated = json.loads(queue_path.read_text(encoding="utf-8"))
    first = next(item for item in updated["items"] if item["piece_id"] == piece)
    assert first["labels"][0]["synthetic"] is False
    assert first["status"] == "pending"

    app = ReviewApp(queue_path)
    status, content_type, body = app.dispatch("GET", "/", b"")
    assert status == 200
    assert "html" in content_type
    assert b"Nortia" in body
    missing = app.dispatch("POST", "/decide", b"")
    assert missing[0] == 400
    health = app.dispatch("GET", "/health", b"")
    assert health[0] == 200
    assert app.dispatch("GET", "/nope", b"")[0] == 404

    seen: dict[str, object] = {}

    def factory(address: tuple[str, int], handler: type) -> object:
        class _Server:
            def serve_forever(self) -> None:
                seen["address"] = address
                seen["handler"] = handler

        return _Server()

    serve(queue_path, 8765, server_factory=factory)
    assert seen["address"] == ("127.0.0.1", 8765)


def test_render_escapes_html() -> None:
    page = render_queue(
        [
            {
                "title": "<script>",
                "piece_id": "p",
                "status": "pending",
                "required_raters": 2,
                "body": "x",
                "claims": [{"text": "<b>", "citation_ids": ["F-1"]}],
                "labels": [],
            }
        ]
    )
    assert "<script>" not in page
    assert "&lt;script&gt;" in page


def test_config_and_openai_guard(repo_root: Path, tmp_path: Path) -> None:
    assert find_root(repo_root / "src") == repo_root
    with pytest.raises(ConfigError):
        find_root(tmp_path)
    with pytest.raises(ConfigError):
        load_settings({"HEMP_PROVIDER": "vendor"}, root=repo_root)
    with pytest.raises(ConfigError):
        load_settings({"HEMP_COST_CAP_USD": "0"}, root=repo_root)
    settings = load_settings({}, root=repo_root)
    assert settings.provider == "cassette"
    assert settings.allow_network is False
    live = LiveConfig(
        base_url="https://example.invalid/v1",
        api_key="local-test-key",
        model="fake-model",
        model_writer="writer-model",
        model_verifier="fake-model",
        model_critic="fake-model",
        max_output_tokens=32,
        timeout_s=5.0,
        max_spend_usd=1.0,
        price_in_per_mtok=1.0,
        price_out_per_mtok=1.0,
        max_live_tokens=None,
    )
    with pytest.raises(ConfigError, match="LIVE_LLM"):
        from hemp.config import load_live_config

        load_live_config({})
    with pytest.raises(ConfigError):
        build_provider(
            provider="openai",
            allow_network=True,
            api_key="",
            base_url="https://example.invalid",
            model="m",
            cassette_path="",
        )
    cassette = tmp_path / "cassette.json"
    cassette.write_text(
        json.dumps(
            {
                "model": "fake-cassette-v1",
                "notes": "synthetic",
                "steps": {
                    "writer:outline": {
                        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                        "content": {"ok": True},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    provider = build_provider(
        provider="cassette",
        allow_network=False,
        api_key="",
        base_url="",
        model="",
        cassette_path=str(cassette),
    )
    assert provider.name == "cassette"
    parsed = parse_chat_response(
        {"choices": [{"message": {"content": '{"lesson": "L1"}'}}], "usage": {"prompt_tokens": 3}}
    )
    assert parsed == {"lesson": "L1"}
    with pytest.raises(SchemaError):
        parse_chat_response({"choices": []})
    body = LlmOpenAICompatible(live, sleep=lambda _seconds: None).build_body(CompletionRequest("writer", "outline", {}))
    assert body["temperature"] == 0
    assert body["model"] == "writer-model"
    assert scan_repo(repo_root) == []


def test_load_rejects_bad_course(tmp_path: Path) -> None:
    path = tmp_path / "course.json"
    path.write_text('{"org": "x"}', encoding="utf-8")
    with pytest.raises(SchemaError):
        load_course(path)
    path.write_text("{", encoding="utf-8")
    with pytest.raises(SchemaError):
        read_json(path)
