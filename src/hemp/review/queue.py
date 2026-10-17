from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from hemp.errors import SchemaError
from hemp.load import read_json, write_json
from hemp.models import QueueItem, ReviewLabel


def decide(item: QueueItem, mins: Mapping[str, int]) -> QueueItem:
    """Approve on means once enough labels exist. Safety must clear for every rater."""
    if len(item.labels) < item.required_raters:
        return item.with_labels(item.labels, "pending")
    for label in item.labels:
        if any(dimension not in label.scores for dimension in mins):
            return item.with_labels(item.labels, "rejected")
        if label.scores["safety"] < mins["safety"]:
            return item.with_labels(item.labels, "rejected")
    for dimension, minimum in mins.items():
        mean = sum(label.scores[dimension] for label in item.labels) / len(item.labels)
        if mean < minimum:
            return item.with_labels(item.labels, "rejected")
    return item.with_labels(item.labels, "approved")


def add_label(item: QueueItem, label: ReviewLabel, mins: Mapping[str, int]) -> QueueItem:
    kept = tuple(existing for existing in item.labels if existing.rater_id != label.rater_id)
    return decide(item.with_labels((*kept, label), item.status), mins)


def dump_queue(
    items: tuple[QueueItem, ...],
    *,
    rubric_version: str,
    mins: Mapping[str, int],
) -> dict[str, object]:
    return {
        "approval_note": (
            "Labels with synthetic=true were generated, not collected from people. "
            "A local decide/serve action can add synthetic=false."
        ),
        "items": [item.to_dict() for item in items],
        "mins": dict(mins),
        "rubric_version": rubric_version,
    }


def save_queue(path: Path, payload: dict[str, object]) -> None:
    write_json(path, payload)


def _label(raw: object) -> ReviewLabel:
    if not isinstance(raw, dict):
        raise SchemaError("label must be an object")
    rater = raw.get("rater_id")
    scores = raw.get("scores")
    synthetic = raw.get("synthetic")
    if not isinstance(rater, str) or not rater:
        raise SchemaError("rater_id must be a string")
    if not isinstance(scores, dict):
        raise SchemaError("scores must be an object")
    if not isinstance(synthetic, bool):
        raise SchemaError("synthetic must be a boolean")
    parsed: dict[str, int] = {}
    for key, value in scores.items():
        if not isinstance(key, str) or isinstance(value, bool) or not isinstance(value, int):
            raise SchemaError("score values must be integers")
        parsed[key] = value
    return ReviewLabel(rater, parsed, synthetic)


def _item(raw: object) -> QueueItem:
    if not isinstance(raw, dict):
        raise SchemaError("queue item must be an object")
    claims_raw = raw.get("claims")
    if not isinstance(claims_raw, list):
        raise SchemaError("claims must be a list")
    claims: list[dict[str, object]] = []
    for claim in claims_raw:
        if not isinstance(claim, dict):
            raise SchemaError("claim must be an object")
        claims.append(dict(claim))
    labels_raw = raw.get("labels")
    if not isinstance(labels_raw, list):
        raise SchemaError("labels must be a list")
    judge = raw.get("judge_scores")
    if not isinstance(judge, dict):
        raise SchemaError("judge_scores must be an object")
    judge_scores: dict[str, int] = {}
    for key, value in judge.items():
        if not isinstance(key, str) or isinstance(value, bool) or not isinstance(value, int):
            raise SchemaError("judge scores must be integers")
        judge_scores[key] = value
    confidence = raw.get("judge_confidence")
    required = raw.get("required_raters")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise SchemaError("judge_confidence must be a number")
    if isinstance(required, bool) or not isinstance(required, int):
        raise SchemaError("required_raters must be an integer")
    for key in ("piece_id", "lesson_id", "title", "rubric_version", "status", "body"):
        if not isinstance(raw.get(key), str):
            raise SchemaError(f"{key} must be a string")
    return QueueItem(
        piece_id=str(raw["piece_id"]),
        lesson_id=str(raw["lesson_id"]),
        title=str(raw["title"]),
        rubric_version=str(raw["rubric_version"]),
        judge_scores=judge_scores,
        judge_confidence=float(confidence),
        required_raters=required,
        labels=tuple(_label(label) for label in labels_raw),
        status=str(raw["status"]),
        body=str(raw["body"]),
        claims=tuple(claims),
    )


def load_queue(path: Path) -> tuple[str, dict[str, int], tuple[QueueItem, ...]]:
    data = read_json(path)
    if not isinstance(data, dict):
        raise SchemaError("queue must be an object")
    version = data.get("rubric_version")
    mins_raw = data.get("mins")
    items_raw = data.get("items")
    if not isinstance(version, str) or not isinstance(mins_raw, dict) or not isinstance(items_raw, list):
        raise SchemaError("queue file is missing rubric_version, mins, or items")
    mins: dict[str, int] = {}
    for key, value in mins_raw.items():
        if not isinstance(key, str) or isinstance(value, bool) or not isinstance(value, int):
            raise SchemaError("mins must map strings to integers")
        mins[key] = value
    return version, mins, tuple(_item(item) for item in items_raw)
