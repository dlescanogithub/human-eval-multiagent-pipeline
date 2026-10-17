from __future__ import annotations

from hemp.config import Policy
from hemp.models import CheckResult, Corpus, CourseSpec, Finding, Lesson, Rubric
from hemp.similarity import contains_term, jaccard, sentences, tokenize

DENY_PHRASES = (
    "publish without review",
    "ignore the reviewer",
    "skip the citation",
    "bypass approval",
)


def course_objective_findings(
    course: CourseSpec,
    accepted: tuple[Lesson, ...],
) -> tuple[Finding, ...]:
    covered = {objective_id for lesson in accepted for objective_id in lesson.objective_ids}
    missing = [item.id for item in course.objectives if item.id not in covered]
    if not missing:
        return ()
    return (
        Finding(
            "objective_gap",
            "accepted lessons do not cover: " + ", ".join(missing),
            None,
        ),
    )


def check_lesson(
    lesson: Lesson,
    *,
    course: CourseSpec,
    corpus: Corpus,
    policy: Policy,
    rubric: Rubric,
    earlier_outline_ids: tuple[str, ...],
    accepted_ids: tuple[str, ...],
    accepted_bodies: tuple[str, ...],
    accepted_sentences: tuple[str, ...],
) -> CheckResult:
    findings: list[Finding] = []
    facts = corpus.by_id()
    known_objectives = set(course.objective_ids())

    if not lesson.topics:
        findings.append(Finding("missing_topics", "lesson has no topics", lesson.id))

    for objective_id in lesson.objective_ids:
        if objective_id not in known_objectives:
            findings.append(Finding("unknown_objective", f"unknown objective {objective_id}", lesson.id))

    for prerequisite_id in lesson.prerequisite_ids:
        if prerequisite_id not in earlier_outline_ids:
            findings.append(
                Finding(
                    "prerequisite_order",
                    f"{prerequisite_id} is not an earlier lesson",
                    lesson.id,
                )
            )
        elif prerequisite_id not in accepted_ids:
            findings.append(
                Finding(
                    "prerequisite_not_accepted",
                    f"{prerequisite_id} was not accepted",
                    lesson.id,
                )
            )

    for claim in lesson.claims:
        if not claim.citation_ids:
            findings.append(Finding("uncited_claim", f"{claim.id} has no citation", lesson.id))
            continue
        for citation_id in claim.citation_ids:
            fact = facts.get(citation_id)
            if fact is None:
                findings.append(Finding("unknown_citation", f"{claim.id} cites {citation_id}", lesson.id))
                continue
            overlap = jaccard(claim.text, fact.text)
            if overlap < policy.groundedness_jaccard_min:
                findings.append(
                    Finding(
                        "weak_grounding",
                        f"{claim.id} does not overlap {citation_id} ({overlap:.2f})",
                        lesson.id,
                    )
                )

    cited_text = " ".join(claim.text for claim in lesson.claims if claim.citation_ids)
    for fact in corpus.facts:
        for term in fact.terms:
            if contains_term(lesson.body, term) and not contains_term(cited_text, term):
                findings.append(Finding("uncited_term", f"body uses {term!r} without a cited claim", lesson.id))

    max_similarity = 0.0
    for prior in accepted_bodies:
        max_similarity = max(max_similarity, jaccard(lesson.body, prior))
    if accepted_bodies and max_similarity >= policy.redundancy_jaccard_max:
        findings.append(
            Finding(
                "redundancy",
                f"body overlaps earlier material ({max_similarity:.2f})",
                lesson.id,
            )
        )

    for sentence in sentences(lesson.body):
        if len(tokenize(sentence)) < policy.repetition_min_tokens:
            continue
        for prior in accepted_sentences:
            if len(tokenize(prior)) < policy.repetition_min_tokens:
                continue
            overlap = jaccard(sentence, prior)
            if overlap >= policy.repetition_jaccard_max:
                findings.append(Finding("repetition", f"sentence repeats earlier text ({overlap:.2f})", lesson.id))
                break

    blob = (lesson.body + " " + " ".join(claim.text for claim in lesson.claims)).lower()
    if any(phrase in blob for phrase in DENY_PHRASES):
        findings.append(Finding("safety", "content asks to skip a control", lesson.id))

    word_count = len(tokenize(lesson.body))
    if word_count < 8 or word_count > 180 or not lesson.title:
        findings.append(Finding("clarity", f"body length {word_count} is outside 8..180", lesson.id))

    scores = _scores(findings, max_similarity, policy, rubric)
    for dimension in rubric.dimensions:
        if scores[dimension.id] < dimension.min_pass and not any(
            finding.code == dimension.id or _score_already_explained(dimension.id, finding.code) for finding in findings
        ):
            findings.append(
                Finding(
                    dimension.id,
                    f"{dimension.id} score {scores[dimension.id]} is below {dimension.min_pass}",
                    lesson.id,
                )
            )
    return CheckResult(tuple(findings), scores)


def _score_already_explained(dimension_id: str, code: str) -> bool:
    mapping = {
        "accuracy": {"uncited_claim", "unknown_citation", "weak_grounding", "uncited_term"},
        "clarity": {"clarity"},
        "flow": {"prerequisite_order", "prerequisite_not_accepted", "missing_topics"},
        "no_redundancy": {"redundancy", "repetition"},
        "safety": {"safety"},
    }
    return code in mapping.get(dimension_id, set())


def _scores(
    findings: list[Finding],
    max_similarity: float,
    policy: Policy,
    rubric: Rubric,
) -> dict[str, int]:
    codes = {finding.code for finding in findings}
    accuracy_codes = {"uncited_claim", "unknown_citation", "weak_grounding", "uncited_term"}
    accuracy = 2 if codes & accuracy_codes else 5
    clarity = 2 if "clarity" in codes else 5
    flow_codes = {"prerequisite_order", "prerequisite_not_accepted", "missing_topics"}
    flow = 1 if codes & flow_codes else 5
    if codes & {"redundancy", "repetition"} or max_similarity >= policy.redundancy_jaccard_max:
        redundancy = 2
    elif max_similarity >= 0.25:
        redundancy = 4
    else:
        redundancy = 5
    safety = 1 if "safety" in codes else 5
    scores = {
        "accuracy": accuracy,
        "clarity": clarity,
        "flow": flow,
        "no_redundancy": redundancy,
        "safety": safety,
    }
    missing = [dimension.id for dimension in rubric.dimensions if dimension.id not in scores]
    if missing:
        raise RuntimeError("checker missed a rubric dimension: " + ",".join(missing))
    return scores
