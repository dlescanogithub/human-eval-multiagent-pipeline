from __future__ import annotations

from pathlib import Path

import pytest

from hemp.checker import check_lesson
from hemp.config import Policy
from hemp.costing import compute_cost
from hemp.load import load_corpus, load_cost_card, load_course, load_drift_weeks, load_rubric
from hemp.models import Claim, Lesson, QueueItem, ReviewLabel, Usage
from hemp.review.drift import drift_report
from hemp.review.queue import add_label, decide
from hemp.review.sampling import required_raters
from hemp.similarity import sentences


def _lesson(body: str, claims: tuple[Claim, ...]) -> Lesson:
    return Lesson(
        id="L1",
        title="Waybills and handoff tokens",
        objective_ids=("OBJ-WAYBILL",),
        prerequisite_ids=(),
        topics=("waybill",),
        body=body,
        claims=claims,
    )


def test_weak_grounding_and_safety_and_redundancy(repo_root: Path) -> None:
    course = load_course(repo_root / "fixtures/course/nortia_logistics.json")
    corpus = load_corpus(repo_root / "fixtures/corpus/nortia_public_style.json")
    rubric = load_rubric(repo_root / "rubrics/rubric-v1.json")
    policy = Policy()
    weak = _lesson(
        "Painting remains a hobby for this short example sentence.",
        (Claim("c1", "painting is unrelated to the cited card", ("F-WAYBILL",)),),
    )
    weak_result = check_lesson(
        weak,
        course=course,
        corpus=corpus,
        policy=policy,
        rubric=rubric,
        earlier_outline_ids=(),
        accepted_ids=(),
        accepted_bodies=(),
        accepted_sentences=(),
    )
    assert "weak_grounding" in {item.code for item in weak_result.findings}

    fact = corpus.by_id()["F-WAYBILL"].text
    unsafe = _lesson(
        fact + " Please publish without review.",
        (Claim("c1", fact, ("F-WAYBILL",)),),
    )
    unsafe_result = check_lesson(
        unsafe,
        course=course,
        corpus=corpus,
        policy=policy,
        rubric=rubric,
        earlier_outline_ids=(),
        accepted_ids=(),
        accepted_bodies=(),
        accepted_sentences=(),
    )
    assert "safety" in {item.code for item in unsafe_result.findings}

    clean = _lesson(
        fact + " Learners record the token before a shipment leaves the dock.", (Claim("c1", fact, ("F-WAYBILL",)),)
    )
    repeated = check_lesson(
        clean,
        course=course,
        corpus=corpus,
        policy=policy,
        rubric=rubric,
        earlier_outline_ids=("L0",),
        accepted_ids=("L0",),
        accepted_bodies=(clean.body,),
        accepted_sentences=sentences(clean.body),
    )
    codes = {item.code for item in repeated.findings}
    assert "redundancy" in codes
    assert "repetition" in codes


def test_sampling_and_decide() -> None:
    policy = Policy()
    assert required_raters(0.9, policy) == 2
    assert required_raters(0.55, policy) == 3
    scores = {"accuracy": 5, "clarity": 5, "flow": 5, "no_redundancy": 5, "safety": 5}
    item = QueueItem(
        piece_id="NL:L1",
        lesson_id="L1",
        title="t",
        rubric_version="1.0.0",
        judge_scores=scores,
        judge_confidence=0.9,
        required_raters=2,
        labels=(),
        status="pending",
        body="body",
        claims=(),
    )
    mins = {"accuracy": 4, "clarity": 3, "flow": 3, "no_redundancy": 4, "safety": 5}
    assert decide(item, mins).status == "pending"
    one = add_label(item, ReviewLabel("local-1", scores, False), mins)
    assert one.status == "pending"
    two = add_label(one, ReviewLabel("local-2", scores, False), mins)
    assert two.status == "approved"
    unsafe_scores = dict(scores)
    unsafe_scores["safety"] = 1
    rejected = add_label(
        add_label(item, ReviewLabel("local-1", unsafe_scores, False), mins),
        ReviewLabel("local-2", unsafe_scores, False),
        mins,
    )
    assert rejected.status == "rejected"


def test_cost_and_drift(repo_root: Path) -> None:
    card = load_cost_card(repo_root / "fixtures/cost/illustrative_rates.json")
    scores = {"accuracy": 5, "clarity": 5, "flow": 5, "no_redundancy": 5, "safety": 5}
    item = QueueItem(
        piece_id="p",
        lesson_id="L1",
        title="t",
        rubric_version="1.0.0",
        judge_scores=scores,
        judge_confidence=1.0,
        required_raters=1,
        labels=(ReviewLabel("r", scores, True),),
        status="approved",
        body="b",
        claims=(),
    )
    report = compute_cost(
        card=card,
        usage=Usage(1000, 0),
        items=(item,),
        attempted_lessons=1,
        cap_usd=1.0,
    )
    assert report["label"] == "simulated"
    assert report["within_cap"] is False
    tiny = compute_cost(
        card=card,
        usage=Usage(0, 0),
        items=(),
        attempted_lessons=0,
        cap_usd=1.0,
    )
    assert tiny["per_approved_piece_usd"] is None
    assert tiny["within_cap"] is True

    disclaimer, threshold, weeks = load_drift_weeks(repo_root / "fixtures/drift/simulated_weeks.json")
    drift = drift_report(weeks, threshold=threshold, disclaimer=disclaimer)
    assert drift["label"] == "simulated"
    assert drift["alert_weeks"] == ["W4"]
    with pytest.raises(ValueError):
        drift_report(weeks[:2], threshold=threshold, disclaimer=disclaimer, baseline_weeks=2)
