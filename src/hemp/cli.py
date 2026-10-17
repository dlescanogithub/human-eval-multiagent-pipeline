from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from hemp import __version__
from hemp.config import Policy, find_root, load_settings
from hemp.evalkit.runner import default_cases, exit_code, format_report, run_case
from hemp.load import (
    load_corpus,
    load_cost_card,
    load_course,
    load_drift_weeks,
    load_rubric,
    write_json,
)
from hemp.logging_setup import configure_logging, log_event
from hemp.models import Corpus, CostCard, CourseSpec, PipelineResult, ReviewLabel, Rubric
from hemp.pipeline import generate_course, run_course
from hemp.providers.cassette import CassetteProvider
from hemp.providers.retry import RetryingProvider
from hemp.review.drift import drift_report
from hemp.review.queue import add_label, dump_queue, load_queue, save_queue
from hemp.review.server import serve
from hemp.secretscan import main as secretscan_main

LOGGER_NAME = "hemp.cli"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hemp")
    parser.add_argument("--root", type=Path, default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="run the happy cassette and write a synthetic report")
    demo.add_argument("--artifact-dir", default="artifacts/demo")

    generate = sub.add_parser("generate", help="enqueue lessons and publish nothing")
    generate.add_argument("--artifact-dir", default="artifacts/generate")

    sub.add_parser("eval", help="invariant gate on the happy cassette")
    sub.add_parser("eval-regression", help="bad cassettes; exits 1 when the gate goes red")

    review = sub.add_parser("review")
    review_sub = review.add_subparsers(dest="review_command", required=True)
    listing = review_sub.add_parser("list")
    listing.add_argument("--queue", required=True)
    decide = review_sub.add_parser("decide")
    decide.add_argument("--queue", required=True)
    decide.add_argument("--piece", required=True)
    decide.add_argument("--rater", required=True)
    decide.add_argument("--scores", required=True, help="accuracy=5,clarity=4,flow=4,...")
    decide.add_argument("--synthetic", action="store_true")
    server = review_sub.add_parser("serve")
    server.add_argument("--queue", required=True)
    server.add_argument("--port", type=int, default=8765)

    drift = sub.add_parser("drift")
    drift.add_argument("--input", default="fixtures/drift/simulated_weeks.json")
    sub.add_parser("secretscan")

    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else find_root()
    settings = load_settings(root=root)
    configure_logging(settings.log_level)
    if args.command == "demo":
        return _demo(root, Path(args.artifact_dir), synthetic=True)
    if args.command == "generate":
        return _demo(root, Path(args.artifact_dir), synthetic=False)
    if args.command == "eval":
        return _eval(root, expect_red=False)
    if args.command == "eval-regression":
        return _eval(root, expect_red=True)
    if args.command == "drift":
        return _drift(root, Path(args.input))
    if args.command == "secretscan":
        return secretscan_main([str(root)])
    if args.command == "review":
        return _review(args)
    return 2


def _policy(root: Path) -> Policy:
    settings = load_settings(root=root)
    base = Policy()
    return Policy(
        max_revisions=base.max_revisions,
        redundancy_jaccard_max=base.redundancy_jaccard_max,
        repetition_jaccard_max=base.repetition_jaccard_max,
        repetition_min_tokens=base.repetition_min_tokens,
        groundedness_jaccard_min=base.groundedness_jaccard_min,
        uncertainty_threshold=base.uncertainty_threshold,
        base_reviews=base.base_reviews,
        uncertain_reviews=base.uncertain_reviews,
        max_attempts=base.max_attempts,
        backoff_base_seconds=base.backoff_base_seconds,
        backoff_cap_seconds=base.backoff_cap_seconds,
        cost_cap_simulated_usd=settings.cost_cap_simulated_usd,
        rater_seed=base.rater_seed,
    )


def _load_happy(root: Path) -> tuple[CourseSpec, Corpus, Rubric, CostCard, CassetteProvider]:
    course = load_course(root / "fixtures" / "course" / "nortia_logistics.json")
    corpus = load_corpus(root / "fixtures" / "corpus" / "nortia_public_style.json")
    rubric = load_rubric(root / "rubrics" / "rubric-v1.json")
    card = load_cost_card(root / "fixtures" / "cost" / "illustrative_rates.json")
    cassette = CassetteProvider.load(root / "fixtures" / "cassettes" / "happy.json")
    return course, corpus, rubric, card, cassette


def _demo(root: Path, artifact_dir: Path, *, synthetic: bool) -> int:
    if not artifact_dir.is_absolute():
        artifact_dir = root / artifact_dir
    course, corpus, rubric, card, cassette = _load_happy(root)
    policy = _policy(root)
    provider = RetryingProvider(cassette, policy, sleep=lambda _seconds: None)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    if synthetic:
        result = run_course(
            course=course,
            corpus=corpus,
            rubric=rubric,
            provider=provider,
            policy=policy,
            card=card,
            trace_path=artifact_dir / "trace.jsonl",
        )
    else:
        result = generate_course(
            course=course,
            corpus=corpus,
            rubric=rubric,
            provider=provider,
            policy=policy,
            trace_path=artifact_dir / "trace.jsonl",
        )
    disclaimer, threshold, weeks = load_drift_weeks(root / "fixtures" / "drift" / "simulated_weeks.json")
    drift = drift_report(weeks, threshold=threshold, disclaimer=disclaimer)
    queue_payload = dump_queue(result.items, rubric_version=rubric.version, mins=rubric.mins())
    save_queue(artifact_dir / "queue.json", queue_payload)
    report = _public_report(result, drift)
    write_json(artifact_dir / "report.json", report)
    if result.agreement is not None:
        write_json(artifact_dir / "agreement.json", result.agreement)
    if result.cost is not None:
        write_json(artifact_dir / "cost.json", result.cost)
    write_json(artifact_dir / "drift.json", drift)
    print(_format_demo(report))
    log_event(
        logging.getLogger(LOGGER_NAME),
        "demo_written",
        artifact_dir=str(artifact_dir),
        synthetic=synthetic,
    )
    if synthetic and report["published"] != report["lessons"]:
        return 1
    if not synthetic and report["published"] != 0:
        return 1
    return 0


def _public_report(result: PipelineResult, drift: dict[str, object]) -> dict[str, object]:
    return {
        "label": "100% synthetic; fictional domain",
        "version": __version__,
        "course_id": result.course_id,
        "rubric_version": result.rubric_version,
        "provider": result.provider_name,
        "approval_basis": result.approval_basis,
        "lessons": len(result.lessons),
        "published": sum(1 for item in result.items if item.status == "approved"),
        "pending": sum(1 for item in result.items if item.status == "pending"),
        "lesson_rows": [
            {
                "id": run.lesson.id,
                "accepted": run.accepted,
                "writer_calls": run.writer_calls,
                "published": bool(run.item and run.item.status == "approved"),
                "finding_codes": [finding.code for finding in run.findings],
                "required_raters": None if run.item is None else run.item.required_raters,
                "judge_confidence": run.critic_confidence,
            }
            for run in result.lessons
        ],
        "agreement": result.agreement,
        "cost": result.cost,
        "drift_alert_weeks": drift.get("alert_weeks"),
        "effects": list(result.effects),
    }


def _format_demo(report: dict[str, object]) -> str:
    rows = report["lesson_rows"]
    assert isinstance(rows, list)
    lines = [
        "Nortia Learning — Foundations of Fictional Logistics",
        "100% synthetic; fictional domain. This demo does not call a paid API.",
        f"approval_basis={report['approval_basis']} published={report['published']} pending={report['pending']}",
    ]
    for row in rows:
        assert isinstance(row, dict)
        lines.append(
            f"- {row['id']}: writer_calls={row['writer_calls']} accepted={row['accepted']} "
            f"published={row['published']} raters={row['required_raters']}"
        )
    cost = report.get("cost")
    if isinstance(cost, dict):
        lines.append(
            "simulated cost "
            f"total_usd={cost.get('total_usd')} per_approved={cost.get('per_approved_piece_usd')} "
            f"all_human_baseline={cost.get('all_human_baseline_usd')} [EST rates]"
        )
    agreement = report.get("agreement")
    if isinstance(agreement, dict) and agreement.get("status") == "computed":
        lines.append(
            "synthetic agreement "
            f"cohen_overall={agreement.get('cohens_kappa_rater1_rater2')} "
            f"cohen_clarity={agreement.get('cohens_kappa_clarity')} "
            f"judge_vs_majority={agreement.get('judge_vs_majority_kappa')} "
            "(not a human study)"
        )
    lines.append(f"simulated drift alert weeks: {report.get('drift_alert_weeks')}")
    return "\n".join(lines)


def _eval(root: Path, *, expect_red: bool) -> int:
    happy, repeat, uncited = default_cases(root)
    cases = [repeat, uncited] if expect_red else [happy]
    reports = [run_case(case, _policy(root)) for case in cases]
    code = exit_code(reports, expect_red=expect_red)
    print(format_report(reports, expect_red=expect_red, code=code), end="")
    return code


def _drift(root: Path, path: Path) -> int:
    source = path if path.is_absolute() else root / path
    disclaimer, threshold, weeks = load_drift_weeks(source)
    report = drift_report(weeks, threshold=threshold, disclaimer=disclaimer)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def _review(args: argparse.Namespace) -> int:
    if args.review_command == "list":
        _version, _mins, items = load_queue(Path(args.queue))
        for item in items:
            print(f"{item.piece_id}\t{item.status}\tlabels={len(item.labels)}/{item.required_raters}")
        return 0
    if args.review_command == "serve":
        serve(Path(args.queue), args.port)
        return 0
    if args.review_command == "decide":
        version, mins, items = load_queue(Path(args.queue))
        scores = _parse_scores(args.scores)
        label = ReviewLabel(args.rater, scores, bool(args.synthetic))
        updated = []
        found = False
        for item in items:
            if item.piece_id == args.piece:
                updated.append(add_label(item, label, mins))
                found = True
            else:
                updated.append(item)
        if not found:
            print(f"unknown piece {args.piece}")
            return 2
        save_queue(Path(args.queue), dump_queue(tuple(updated), rubric_version=version, mins=mins))
        match = next(item for item in updated if item.piece_id == args.piece)
        print(f"{match.piece_id} {match.status} synthetic={label.synthetic}")
        return 0
    return 2


def _parse_scores(raw: str) -> dict[str, int]:
    scores: dict[str, int] = {}
    for part in raw.split(","):
        key, value = part.split("=", 1)
        scores[key.strip()] = int(value.strip())
    return scores
