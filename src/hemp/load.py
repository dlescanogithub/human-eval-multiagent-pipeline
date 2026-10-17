from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hemp.errors import SchemaError
from hemp.models import (
    Claim,
    Corpus,
    CostCard,
    CourseSpec,
    CriticNote,
    Dimension,
    Fact,
    Lesson,
    LessonSpec,
    Objective,
    Outline,
    Rubric,
    Usage,
)

REQUIRED_DIMENSIONS = ("accuracy", "clarity", "flow", "no_redundancy", "safety")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SchemaError(f"{path} is not valid JSON") from exc


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _obj(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SchemaError(f"{label} must be an object")
    return value


def _str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SchemaError(f"{key} must be a non-empty string")
    return value


def _str_tuple(data: dict[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SchemaError(f"{key} must be a list of strings")
    return tuple(value)


def _int(value: object, key: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaError(f"{key} must be an integer")
    return value


def _float(value: object, key: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchemaError(f"{key} must be a number")
    return float(value)


def parse_usage(data: dict[str, Any]) -> Usage:
    raw = data.get("usage", {})
    usage = _obj(raw, "usage")
    prompt = _int(usage.get("prompt_tokens"), "prompt_tokens")
    completion = _int(usage.get("completion_tokens"), "completion_tokens")
    if prompt < 0 or completion < 0:
        raise SchemaError("token counts must be >= 0")
    return Usage(prompt, completion)


def load_course(path: Path) -> CourseSpec:
    data = _obj(read_json(path), "course")
    raw_objectives = data.get("objectives")
    if not isinstance(raw_objectives, list) or not raw_objectives:
        raise SchemaError("objectives must be a non-empty list")
    objectives: list[Objective] = []
    for item in raw_objectives:
        body = _obj(item, "objective")
        objectives.append(Objective(_str(body, "id"), _str(body, "text")))
    ids = [item.id for item in objectives]
    if len(ids) != len(set(ids)):
        raise SchemaError("objective ids must be unique")
    return CourseSpec(_str(data, "org"), _str(data, "course_id"), _str(data, "title"), tuple(objectives))


def load_corpus(path: Path) -> Corpus:
    data = _obj(read_json(path), "corpus")
    raw_facts = data.get("facts")
    if not isinstance(raw_facts, list) or not raw_facts:
        raise SchemaError("facts must be a non-empty list")
    facts: list[Fact] = []
    for item in raw_facts:
        body = _obj(item, "fact")
        facts.append(Fact(_str(body, "id"), _str(body, "text"), _str_tuple(body, "terms"), _str(body, "source")))
    ids = [fact.id for fact in facts]
    if len(ids) != len(set(ids)):
        raise SchemaError("fact ids must be unique")
    label = data.get("label", "")
    if label != "synthetic":
        raise SchemaError("corpus label must be synthetic")
    return Corpus(_str(data, "id"), label, tuple(facts))


def load_rubric(path: Path) -> Rubric:
    data = _obj(read_json(path), "rubric")
    raw_dims = data.get("dimensions")
    if not isinstance(raw_dims, list):
        raise SchemaError("dimensions must be a list")
    dimensions: list[Dimension] = []
    for item in raw_dims:
        body = _obj(item, "dimension")
        scale_min = _int(body.get("scale_min"), "scale_min")
        scale_max = _int(body.get("scale_max"), "scale_max")
        minimum = _int(body.get("min_pass"), "min_pass")
        if scale_min >= scale_max or minimum < scale_min or minimum > scale_max:
            raise SchemaError("rubric scale is inconsistent")
        dimensions.append(Dimension(_str(body, "id"), minimum, scale_min, scale_max))
    rubric = Rubric(_str(data, "version"), tuple(dimensions), _str(data, "publish_rule"))
    if rubric.ids() != REQUIRED_DIMENSIONS:
        raise SchemaError("rubric dimensions must be accuracy, clarity, flow, no_redundancy, safety")
    return rubric


def load_cost_card(path: Path) -> CostCard:
    data = _obj(read_json(path), "cost card")
    if data.get("label") != "simulated" or data.get("estimate") is not True:
        raise SchemaError("cost card must be labeled simulated and estimate=true")
    return CostCard(
        label="simulated",
        note=_str(data, "note"),
        ai_usd_per_1k_tokens=_float(data.get("ai_usd_per_1k_tokens"), "ai_usd_per_1k_tokens"),
        human_minutes_per_review=_float(data.get("human_minutes_per_review"), "human_minutes_per_review"),
        human_usd_per_hour=_float(data.get("human_usd_per_hour"), "human_usd_per_hour"),
        all_human_minutes_per_lesson=_float(data.get("all_human_minutes_per_lesson"), "all_human_minutes_per_lesson"),
    )


def load_drift_weeks(path: Path) -> tuple[str, float, tuple[tuple[str, tuple[float, ...]], ...]]:
    data = _obj(read_json(path), "drift")
    if data.get("label") != "simulated":
        raise SchemaError("drift fixture must be labeled simulated")
    threshold = _float(data.get("threshold"), "threshold")
    raw_weeks = data.get("weeks")
    if not isinstance(raw_weeks, list) or len(raw_weeks) < 3:
        raise SchemaError("drift fixture needs at least 3 weeks")
    weeks: list[tuple[str, tuple[float, ...]]] = []
    for item in raw_weeks:
        body = _obj(item, "week")
        scores = body.get("scores")
        if not isinstance(scores, list) or not scores:
            raise SchemaError("week scores must be a non-empty list")
        weeks.append((_str(body, "week"), tuple(_float(score, "score") for score in scores)))
    return _str(data, "disclaimer"), threshold, tuple(weeks)


def parse_outline(content: dict[str, Any]) -> Outline:
    raw_lessons = content.get("lessons")
    if not isinstance(raw_lessons, list) or not raw_lessons:
        raise SchemaError("outline lessons must be a non-empty list")
    lessons: list[LessonSpec] = []
    for item in raw_lessons:
        body = _obj(item, "lesson spec")
        lessons.append(
            LessonSpec(
                _str(body, "id"),
                _str(body, "title"),
                _str_tuple(body, "objective_ids"),
                _str_tuple(body, "prerequisite_ids"),
            )
        )
    ids = [lesson.id for lesson in lessons]
    if len(ids) != len(set(ids)):
        raise SchemaError("outline lesson ids must be unique")
    return Outline(_str(content, "course_id"), _str(content, "title"), tuple(lessons))


def parse_lesson(content: dict[str, Any]) -> Lesson:
    raw_claims = content.get("claims")
    if not isinstance(raw_claims, list) or not raw_claims:
        raise SchemaError("lesson claims must be a non-empty list")
    claims: list[Claim] = []
    for item in raw_claims:
        body = _obj(item, "claim")
        claims.append(Claim(_str(body, "id"), _str(body, "text"), _str_tuple(body, "citation_ids")))
    claim_ids = [claim.id for claim in claims]
    if len(claim_ids) != len(set(claim_ids)):
        raise SchemaError("claim ids must be unique")
    return Lesson(
        _str(content, "id"),
        _str(content, "title"),
        _str_tuple(content, "objective_ids"),
        _str_tuple(content, "prerequisite_ids"),
        _str_tuple(content, "topics"),
        _str(content, "body"),
        tuple(claims),
    )


def parse_critic(content: dict[str, Any], rubric: Rubric) -> CriticNote:
    raw_scores = content.get("scores")
    scores_obj = _obj(raw_scores, "scores")
    scores: dict[str, int] = {}
    for dim in rubric.dimensions:
        scores[dim.id] = _int(scores_obj.get(dim.id), dim.id)
        if scores[dim.id] < dim.scale_min or scores[dim.id] > dim.scale_max:
            raise SchemaError(f"critic score {dim.id} is outside the rubric scale")
    confidence = _float(content.get("confidence"), "confidence")
    if confidence < 0 or confidence > 1:
        raise SchemaError("confidence must be between 0 and 1")
    request = content.get("request_revision")
    safety = content.get("safety_block")
    if not isinstance(request, bool) or not isinstance(safety, bool):
        raise SchemaError("request_revision and safety_block must be booleans")
    comments = _str_tuple(content, "comments")
    return CriticNote(scores, confidence, request, comments, safety, _str(content, "rubric_version"))
