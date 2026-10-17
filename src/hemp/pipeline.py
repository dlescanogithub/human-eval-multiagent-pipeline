from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any

from hemp.checker import check_lesson, course_objective_findings
from hemp.config import Policy
from hemp.costing import compute_cost
from hemp.errors import SchemaError
from hemp.load import parse_critic, parse_lesson, parse_outline
from hemp.logging_setup import log_event
from hemp.models import (
    CheckResult,
    Corpus,
    CostCard,
    CourseSpec,
    Lesson,
    LessonRun,
    PipelineResult,
    QueueItem,
    Rubric,
    RunningSummary,
    Usage,
)
from hemp.providers.base import CompletionRequest, Provider
from hemp.review.agreement import agreement_report
from hemp.review.sampling import required_raters
from hemp.review.synthetic_raters import synthesize_item
from hemp.similarity import sentences
from hemp.trace import TraceLog

LOGGER = logging.getLogger("hemp.pipeline")


def generate_course(
    *,
    course: CourseSpec,
    corpus: Corpus,
    rubric: Rubric,
    provider: Provider,
    policy: Policy,
    clock: Any = None,
    trace_path: Any = None,
) -> PipelineResult:
    """Run outline → lessons → checker. Accepted lessons wait in the queue. Nothing is published."""
    trace = TraceLog(rubric_version=rubric.version, clock=clock, path=trace_path)
    usage = Usage(0, 0)
    trace.add("course_started", course_id=course.course_id, provider=provider.name)
    outline_completion = provider.complete(
        CompletionRequest(
            role="writer",
            step="outline",
            payload={"course_id": course.course_id, "rubric_version": rubric.version},
        )
    )
    usage = usage.add(outline_completion.usage)
    outline = parse_outline(outline_completion.content)
    if outline.course_id != course.course_id:
        raise SchemaError("outline course_id does not match the course spec")
    trace.add(
        "outline_received",
        course_id=course.course_id,
        lesson_ids=[spec.id for spec in outline.lessons],
        provider=outline_completion.provider,
    )

    summary = RunningSummary()
    runs: list[LessonRun] = []
    accepted: list[Lesson] = []
    accepted_bodies: list[str] = []
    accepted_sentences: list[str] = []

    for index, spec in enumerate(outline.lessons):
        earlier = tuple(item.id for item in outline.lessons[:index])
        summary_before = summary.to_dict()
        feedback: dict[str, Any] | None = None
        lesson: Lesson | None = None
        check: CheckResult | None = None
        confidence = 1.0
        writer_calls = 0
        last_request = True
        last_safety = False
        for revision in range(policy.max_revisions):
            step = f"draft:{spec.id}" if revision == 0 else f"revise:{spec.id}:r{revision}"
            trace.add(
                "writer_request",
                lesson_id=spec.id,
                revision=revision,
                summary=summary.to_dict(),
                provider=provider.name,
            )
            completion = provider.complete(
                CompletionRequest(
                    role="writer",
                    step=step,
                    payload={
                        "course_id": course.course_id,
                        "lesson_spec": {
                            "id": spec.id,
                            "title": spec.title,
                            "objective_ids": list(spec.objective_ids),
                            "prerequisite_ids": list(spec.prerequisite_ids),
                        },
                        "running_summary": summary.to_dict(),
                        "feedback": feedback,
                        "rubric_version": rubric.version,
                    },
                )
            )
            usage = usage.add(completion.usage)
            writer_calls += 1
            lesson = parse_lesson(completion.content)
            if (
                lesson.id != spec.id
                or lesson.objective_ids != spec.objective_ids
                or lesson.prerequisite_ids != spec.prerequisite_ids
            ):
                raise SchemaError(f"{spec.id} draft does not match the outline contract")
            trace.add(
                "writer_output",
                lesson_id=lesson.id,
                revision=revision,
                provider=completion.provider,
                model=completion.model,
            )
            agent_step = f"{spec.id}:r{revision}"
            verified = provider.complete(
                CompletionRequest(
                    role="verifier",
                    step=agent_step,
                    payload={"lesson_id": spec.id, "rubric_version": rubric.version},
                )
            )
            usage = usage.add(verified.usage)
            trace.add(
                "verifier_agent",
                lesson_id=spec.id,
                revision=revision,
                provider=verified.provider,
            )
            critique = provider.complete(
                CompletionRequest(
                    role="critic",
                    step=agent_step,
                    payload={"lesson_id": spec.id, "rubric_version": rubric.version},
                )
            )
            usage = usage.add(critique.usage)
            critic = parse_critic(critique.content, rubric)
            if critic.rubric_version != rubric.version:
                raise SchemaError("critic rubric_version does not match the loaded rubric")
            confidence = critic.confidence
            last_request = critic.request_revision
            last_safety = critic.safety_block
            trace.add(
                "critic_agent",
                lesson_id=spec.id,
                revision=revision,
                confidence=critic.confidence,
                request_revision=critic.request_revision,
                safety_block=critic.safety_block,
                provider=critique.provider,
            )
            check = check_lesson(
                lesson,
                course=course,
                corpus=corpus,
                policy=policy,
                rubric=rubric,
                earlier_outline_ids=earlier,
                accepted_ids=tuple(item.id for item in accepted),
                accepted_bodies=tuple(accepted_bodies),
                accepted_sentences=tuple(accepted_sentences),
            )
            trace.add(
                "checker",
                lesson_id=spec.id,
                revision=revision,
                passed=check.passed,
                finding_codes=[finding.code for finding in check.findings],
                scores=check.scores,
            )
            if check.passed and not critic.request_revision and not critic.safety_block:
                break
            feedback = {
                "finding_codes": [finding.code for finding in check.findings],
                "critic_comments": list(critic.comments),
            }
        if lesson is None or check is None:
            raise SchemaError("lesson loop did not run")
        accepted_now = check.passed and not last_request and not last_safety
        item: QueueItem | None = None
        if accepted_now:
            summary = summary.add(lesson)
            accepted.append(lesson)
            accepted_bodies.append(lesson.body)
            accepted_sentences.extend(sentences(lesson.body))
            needed = required_raters(confidence, policy)
            item = QueueItem(
                piece_id=f"{course.course_id}:{lesson.id}",
                lesson_id=lesson.id,
                title=lesson.title,
                rubric_version=rubric.version,
                judge_scores=dict(check.scores),
                judge_confidence=confidence,
                required_raters=needed,
                labels=(),
                status="pending",
                body=lesson.body,
                claims=tuple(
                    {
                        "id": claim.id,
                        "text": claim.text,
                        "citation_ids": list(claim.citation_ids),
                    }
                    for claim in lesson.claims
                ),
            )
            trace.add(
                "review_enqueued",
                piece_id=item.piece_id,
                lesson_id=lesson.id,
                required_raters=needed,
                confidence=confidence,
                actor="pipeline",
            )
        else:
            trace.add(
                "lesson_rejected",
                lesson_id=lesson.id,
                finding_codes=[finding.code for finding in check.findings],
                actor="checker",
            )
        runs.append(
            LessonRun(
                lesson=lesson,
                accepted=accepted_now,
                writer_calls=writer_calls,
                findings=check.findings,
                checker_scores=dict(check.scores),
                critic_confidence=confidence,
                summary_before=summary_before,
                item=item,
            )
        )

    accepted_lessons = tuple(run.lesson for run in runs if run.accepted)
    findings = course_objective_findings(course, accepted_lessons)
    effects = ("queue_human_review",) if any(run.item is not None for run in runs) else ()
    trace.add(
        "course_generated",
        course_id=course.course_id,
        accepted_lesson_ids=[lesson.id for lesson in accepted_lessons],
        course_finding_codes=[finding.code for finding in findings],
    )
    log_event(
        LOGGER,
        "course_generated",
        course_id=course.course_id,
        accepted=len(accepted_lessons),
        provider=provider.name,
    )
    return PipelineResult(
        course_id=course.course_id,
        rubric_version=rubric.version,
        provider_name=provider.name,
        lessons=tuple(runs),
        summary=summary,
        items=tuple(run.item for run in runs if run.item is not None),
        effects=effects,
        trace=tuple(trace.events),
        usage=usage,
        course_findings=findings,
        agreement=None,
        cost=None,
        approval_basis="none",
        max_revisions=policy.max_revisions,
    )


def finalize_synthetic(
    result: PipelineResult,
    *,
    policy: Policy,
    rubric: Rubric,
    card: CostCard,
) -> PipelineResult:
    """Attach seeded synthetic labels and apply the publish rule. Not a human study."""
    mins = rubric.mins()
    items = tuple(
        synthesize_item(item, ordinal=ordinal, policy=policy, mins=mins) for ordinal, item in enumerate(result.items)
    )
    stamped = result.trace[-1]["ts"] if result.trace else ""
    extra: list[dict[str, object]] = []
    for item in items:
        for label in item.labels:
            extra.append(
                {
                    "event": "rater_label",
                    "ts": stamped,
                    "rubric_version": result.rubric_version,
                    "piece_id": item.piece_id,
                    "rater_id": label.rater_id,
                    "synthetic": True,
                    "actor": label.rater_id,
                    "scores": dict(label.scores),
                }
            )
        extra.append(
            {
                "event": "publish_decision",
                "ts": stamped,
                "rubric_version": result.rubric_version,
                "piece_id": item.piece_id,
                "status": item.status,
                "actor": "publish-policy",
                "approved_by": [label.rater_id for label in item.labels],
                "approval_basis": "synthetic",
            }
        )
    by_lesson = {item.lesson_id: item for item in items}
    lessons = tuple(
        replace(run, item=by_lesson[run.lesson.id]) if run.item is not None else run for run in result.lessons
    )
    cost = compute_cost(
        card=card,
        usage=result.usage,
        items=items,
        attempted_lessons=len(result.lessons),
        cap_usd=policy.cost_cap_simulated_usd,
    )
    agreement = agreement_report(items, mins)
    log_event(
        LOGGER,
        "synthetic_review_applied",
        course_id=result.course_id,
        approved=sum(1 for item in items if item.status == "approved"),
    )
    return replace(
        result,
        lessons=lessons,
        items=items,
        trace=result.trace + tuple(extra),
        agreement=agreement,
        cost=cost,
        approval_basis="synthetic",
    )


def run_course(
    *,
    course: CourseSpec,
    corpus: Corpus,
    rubric: Rubric,
    provider: Provider,
    policy: Policy,
    card: CostCard,
    clock: Any = None,
    trace_path: Any = None,
) -> PipelineResult:
    generated = generate_course(
        course=course,
        corpus=corpus,
        rubric=rubric,
        provider=provider,
        policy=policy,
        clock=clock,
        trace_path=trace_path,
    )
    return finalize_synthetic(generated, policy=policy, rubric=rubric, card=card)
