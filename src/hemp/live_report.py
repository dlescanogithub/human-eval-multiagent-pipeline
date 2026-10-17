"""One-page summary of an optional live run. Nothing here is a committed measurement."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hemp.models import PipelineResult

NOT_A_MEASUREMENT = "this run only; not a committed measurement"


def write_run(
    out_dir: Path,
    *,
    result: PipelineResult | None,
    status: str,
    models: dict[str, str],
    pieces: int | None,
    seed: int | None,
    command: str,
    date: str,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = _lesson_rows(result)
    accepted = sum(1 for row in rows if row["accepted"])
    ledger = _read_ledger(out_dir / "spend.jsonl")
    cost_cell, tokens_in, tokens_out = _cost_cell(ledger)
    report: dict[str, Any] = {
        "date": date,
        "status": status,
        "live_result_claimed": False,
        "command": command,
        "pieces": pieces,
        "seed": seed,
        "models": models,
        "n_lessons": len(rows),
        "accepted_by_checker": accepted,
        "published": 0 if result is None else sum(1 for item in result.items if item.status == "approved"),
        "pending": 0 if result is None else sum(1 for item in result.items if item.status == "pending"),
        "lesson_rows": rows,
        "invariant_pass_rates": _rates(rows, accepted),
        "cost": cost_cell,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "ledger_rows": len(ledger),
        "notes": _notes(status),
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "summary.md").write_text(render_markdown(report), encoding="utf-8")
    return report


def render_markdown(report: dict[str, Any]) -> str:
    """A one-page table the owner can paste into docs/LIVE_RUN_TEMPLATE.md."""
    models = report.get("models", {})
    if not isinstance(models, dict):
        models = {}
    pieces = report.get("pieces")
    n_pieces = "all" if pieces is None else str(pieces)
    row = " | ".join(
        [
            str(report.get("date", "")),
            str(models.get("writer", "")),
            str(models.get("verifier", "")),
            str(models.get("critic", "")),
            str(report.get("command", "")),
            n_pieces,
            str(report.get("cost", "")),
            str(report.get("invariant_pass_rates", "")),
            str(report.get("notes", "")),
        ]
    )
    lines = [
        "# Live run",
        "",
        "Not a committed measurement. Paste the row below into docs/LIVE_RUN_TEMPLATE.md after you review it.",
        "",
        (
            "| date | model_writer | model_verifier | model_critic | command "
            "| n_pieces | cost | invariant_pass_rates | notes |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        f"| {row} |",
        "",
        f"status: {report.get('status')}",
        f"live_result_claimed: {str(report.get('live_result_claimed')).lower()}",
        "",
    ]
    return "\n".join(lines)


def load_report(directory: Path) -> dict[str, Any]:
    path = directory / "report.json"
    if not path.is_file():
        raise FileNotFoundError(str(path))
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("report.json must be an object")
    return payload


def _lesson_rows(result: PipelineResult | None) -> list[dict[str, Any]]:
    if result is None:
        return []
    return [
        {
            "id": run.lesson.id,
            "accepted": run.accepted,
            "finding_codes": [finding.code for finding in run.findings],
        }
        for run in result.lessons
    ]


def _rates(rows: list[dict[str, Any]], accepted: int) -> str:
    if not rows:
        return "no lessons completed"
    return f"checker_accepted={accepted}/{len(rows)}; {NOT_A_MEASUREMENT}"


def _notes(status: str) -> str:
    if status == "BUDGET_EXHAUSTED":
        return "budget exhausted; partial report; " + NOT_A_MEASUREMENT
    if status == "finished":
        return "checker judged the drafts; items stay pending; " + NOT_A_MEASUREMENT
    return NOT_A_MEASUREMENT


def _read_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _cost_cell(rows: list[dict[str, Any]]) -> tuple[str, int, int]:
    tokens_in = 0
    tokens_out = 0
    total = 0.0
    unknown = False
    for row in rows:
        tokens_in += int(row.get("tokens_in", 0))
        tokens_out += int(row.get("tokens_out", 0))
        cost = row.get("cost")
        if cost == "unknown" or not isinstance(cost, (int, float)):
            unknown = True
        else:
            total += float(cost)
    if not rows:
        return "not measured yet", 0, 0
    if unknown:
        return "unknown", tokens_in, tokens_out
    return f"{total} USD; {NOT_A_MEASUREMENT}", tokens_in, tokens_out
