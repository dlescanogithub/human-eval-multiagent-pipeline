from __future__ import annotations

from dataclasses import dataclass, replace

from hemp.similarity import digest


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int = 0

    @property
    def total(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def add(self, other: Usage) -> Usage:
        return Usage(
            self.prompt_tokens + other.prompt_tokens,
            self.completion_tokens + other.completion_tokens,
            self.cached_tokens + other.cached_tokens,
        )


@dataclass(frozen=True)
class Objective:
    id: str
    text: str


@dataclass(frozen=True)
class CourseSpec:
    org: str
    course_id: str
    title: str
    objectives: tuple[Objective, ...]

    def objective_ids(self) -> tuple[str, ...]:
        return tuple(item.id for item in self.objectives)


@dataclass(frozen=True)
class Fact:
    id: str
    text: str
    terms: tuple[str, ...]
    source: str


@dataclass(frozen=True)
class Corpus:
    id: str
    label: str
    facts: tuple[Fact, ...]

    def by_id(self) -> dict[str, Fact]:
        return {fact.id: fact for fact in self.facts}


@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    citation_ids: tuple[str, ...]


@dataclass(frozen=True)
class Lesson:
    id: str
    title: str
    objective_ids: tuple[str, ...]
    prerequisite_ids: tuple[str, ...]
    topics: tuple[str, ...]
    body: str
    claims: tuple[Claim, ...]


@dataclass(frozen=True)
class LessonSpec:
    id: str
    title: str
    objective_ids: tuple[str, ...]
    prerequisite_ids: tuple[str, ...]


@dataclass(frozen=True)
class Outline:
    course_id: str
    title: str
    lessons: tuple[LessonSpec, ...]


@dataclass(frozen=True)
class Dimension:
    id: str
    min_pass: int
    scale_min: int
    scale_max: int


@dataclass(frozen=True)
class Rubric:
    version: str
    dimensions: tuple[Dimension, ...]
    publish_rule: str

    def mins(self) -> dict[str, int]:
        return {item.id: item.min_pass for item in self.dimensions}

    def ids(self) -> tuple[str, ...]:
        return tuple(item.id for item in self.dimensions)


@dataclass(frozen=True)
class CostCard:
    label: str
    note: str
    ai_usd_per_1k_tokens: float
    human_minutes_per_review: float
    human_usd_per_hour: float
    all_human_minutes_per_lesson: float


@dataclass(frozen=True)
class RunningSummary:
    lesson_ids: tuple[str, ...] = ()
    topics: tuple[str, ...] = ()
    objective_ids: tuple[str, ...] = ()
    digests: tuple[str, ...] = ()

    def add(self, lesson: Lesson) -> RunningSummary:
        return RunningSummary(
            lesson_ids=(*self.lesson_ids, lesson.id),
            topics=self.topics + lesson.topics,
            objective_ids=self.objective_ids + lesson.objective_ids,
            digests=(*self.digests, digest(lesson.body)),
        )

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "lesson_ids": list(self.lesson_ids),
            "topics": list(self.topics),
            "objective_ids": list(self.objective_ids),
            "digests": list(self.digests),
        }


@dataclass(frozen=True)
class Finding:
    code: str
    message: str
    lesson_id: str | None
    severity: str = "block"

    def to_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "message": self.message,
            "lesson_id": self.lesson_id,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class CheckResult:
    findings: tuple[Finding, ...]
    scores: dict[str, int]

    @property
    def passed(self) -> bool:
        return not self.findings


@dataclass(frozen=True)
class CriticNote:
    scores: dict[str, int]
    confidence: float
    request_revision: bool
    comments: tuple[str, ...]
    safety_block: bool
    rubric_version: str


@dataclass(frozen=True)
class ReviewLabel:
    rater_id: str
    scores: dict[str, int]
    synthetic: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "rater_id": self.rater_id,
            "scores": dict(self.scores),
            "synthetic": self.synthetic,
        }


@dataclass(frozen=True)
class QueueItem:
    piece_id: str
    lesson_id: str
    title: str
    rubric_version: str
    judge_scores: dict[str, int]
    judge_confidence: float
    required_raters: int
    labels: tuple[ReviewLabel, ...]
    status: str
    body: str
    claims: tuple[dict[str, object], ...]

    def with_labels(self, labels: tuple[ReviewLabel, ...], status: str) -> QueueItem:
        return replace(self, labels=labels, status=status)

    def to_dict(self) -> dict[str, object]:
        return {
            "piece_id": self.piece_id,
            "lesson_id": self.lesson_id,
            "title": self.title,
            "rubric_version": self.rubric_version,
            "judge_scores": dict(self.judge_scores),
            "judge_confidence": self.judge_confidence,
            "required_raters": self.required_raters,
            "labels": [label.to_dict() for label in self.labels],
            "status": self.status,
            "body": self.body,
            "claims": [dict(claim) for claim in self.claims],
        }


@dataclass(frozen=True)
class LessonRun:
    lesson: Lesson
    accepted: bool
    writer_calls: int
    findings: tuple[Finding, ...]
    checker_scores: dict[str, int]
    critic_confidence: float
    summary_before: dict[str, list[str]]
    item: QueueItem | None


@dataclass(frozen=True)
class PipelineResult:
    course_id: str
    rubric_version: str
    provider_name: str
    lessons: tuple[LessonRun, ...]
    summary: RunningSummary
    items: tuple[QueueItem, ...]
    effects: tuple[str, ...]
    trace: tuple[dict[str, object], ...]
    usage: Usage
    course_findings: tuple[Finding, ...]
    agreement: dict[str, object] | None
    cost: dict[str, object] | None
    approval_basis: str
    max_revisions: int
