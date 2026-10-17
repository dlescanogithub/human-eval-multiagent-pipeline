from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hemp.config import Policy
from hemp.evalkit.invariants import (
    InvariantOutcome,
    evaluate,
    max_accepted_jaccard,
    recompute_finding_codes,
)
from hemp.load import load_corpus, load_cost_card, load_course, load_drift_weeks, load_rubric
from hemp.pipeline import run_course
from hemp.providers.base import Provider
from hemp.providers.cassette import CassetteProvider
from hemp.providers.retry import RetryingProvider
from hemp.providers.vulnerable import VulnerableProvider
from hemp.review.drift import drift_report

EXIT_OK = 0
EXIT_GATE_RED = 1
EXIT_BROKEN = 2


@dataclass(frozen=True)
class EvalCase:
    name: str
    mode: str
    course_path: Path
    cassette_path: Path
    corpus_path: Path
    rubric_path: Path
    cost_path: Path
    drift_path: Path
    max_revisions: int
    expect_blocking_any: tuple[str, ...]
    require_revision_loop: bool
    provider_kind: str = "cassette"


@dataclass
class EvalReport:
    case_name: str
    mode: str
    outcomes: tuple[InvariantOutcome, ...]
    blocking_codes: tuple[str, ...]
    metrics: dict[str, object]
    broken: bool

    @property
    def safety_passed(self) -> bool:
        return all(item.passed for item in self.outcomes if item.kind == "safety")

    @property
    def quality_passed(self) -> bool:
        return all(item.passed for item in self.outcomes if item.kind == "quality")


def default_cases(root: Path) -> tuple[EvalCase, EvalCase, EvalCase, EvalCase]:
    corpus = root / "fixtures" / "corpus" / "nortia_public_style.json"
    rubric = root / "rubrics" / "rubric-v1.json"
    cost = root / "fixtures" / "cost" / "illustrative_rates.json"
    drift = root / "fixtures" / "drift" / "simulated_weeks.json"
    happy = EvalCase(
        name="happy",
        mode="happy",
        course_path=root / "fixtures" / "course" / "nortia_logistics.json",
        cassette_path=root / "fixtures" / "cassettes" / "happy.json",
        corpus_path=corpus,
        rubric_path=rubric,
        cost_path=cost,
        drift_path=drift,
        max_revisions=3,
        expect_blocking_any=(),
        require_revision_loop=True,
    )
    repeat = EvalCase(
        name="regression_repeat",
        mode="regression",
        course_path=root / "fixtures" / "course" / "regression_repeat.json",
        cassette_path=root / "fixtures" / "cassettes" / "regression_repeat.json",
        corpus_path=corpus,
        rubric_path=rubric,
        cost_path=cost,
        drift_path=drift,
        max_revisions=2,
        expect_blocking_any=("redundancy", "repetition"),
        require_revision_loop=False,
    )
    uncited = EvalCase(
        name="regression_uncited",
        mode="regression",
        course_path=root / "fixtures" / "course" / "regression_uncited.json",
        cassette_path=root / "fixtures" / "cassettes" / "regression_uncited.json",
        corpus_path=corpus,
        rubric_path=rubric,
        cost_path=cost,
        drift_path=drift,
        max_revisions=2,
        expect_blocking_any=("uncited_claim",),
        require_revision_loop=False,
    )
    poison = EvalCase(
        name="regression_poison",
        mode="regression",
        course_path=root / "fixtures" / "course" / "regression_poison.json",
        cassette_path=root / "fixtures" / "cassettes" / "happy.json",
        corpus_path=root / "fixtures" / "corpus" / "poisoned_instruction.json",
        rubric_path=rubric,
        cost_path=cost,
        drift_path=drift,
        max_revisions=1,
        expect_blocking_any=("uncited_claim",),
        require_revision_loop=False,
        provider_kind="vulnerable",
    )
    return happy, repeat, uncited, poison


def run_case(case: EvalCase, policy: Policy | None = None) -> EvalReport:
    base = policy or Policy()
    active = base.with_max_revisions(case.max_revisions)
    course = load_course(case.course_path)
    corpus = load_corpus(case.corpus_path)
    rubric = load_rubric(case.rubric_path)
    card = load_cost_card(case.cost_path)
    disclaimer, threshold, weeks = load_drift_weeks(case.drift_path)
    drift = drift_report(weeks, threshold=threshold, disclaimer=disclaimer)
    inner: Provider = (
        VulnerableProvider() if case.provider_kind == "vulnerable" else CassetteProvider.load(case.cassette_path)
    )
    provider = RetryingProvider(inner, active, sleep=lambda _s: None)
    result = run_course(
        course=course,
        corpus=corpus,
        rubric=rubric,
        provider=provider,
        policy=active,
        card=card,
        clock=lambda: "2026-10-17T00:00:00+00:00",
    )
    outcomes = evaluate(
        result,
        course=course,
        corpus=corpus,
        policy=active,
        rubric=rubric,
        drift=drift,
        require_revision_loop=case.require_revision_loop,
    )
    codes = recompute_finding_codes(result, course=course, corpus=corpus, policy=active, rubric=rubric)
    broken = bool(case.expect_blocking_any) and not any(code in codes for code in case.expect_blocking_any)
    agreement = result.agreement or {}
    cost = result.cost or {}
    metrics: dict[str, object] = {
        "lessons": len(result.lessons),
        "accepted": sum(1 for run in result.lessons if run.accepted),
        "published": sum(1 for item in result.items if item.status == "approved"),
        "writer_calls": {run.lesson.id: run.writer_calls for run in result.lessons},
        "max_accepted_jaccard": round(max_accepted_jaccard(result), 6),
        "prompt_tokens": result.usage.prompt_tokens,
        "completion_tokens": result.usage.completion_tokens,
        "total_usd_simulated": cost.get("total_usd"),
        "per_approved_piece_usd_simulated": cost.get("per_approved_piece_usd"),
        "all_human_baseline_usd_simulated": cost.get("all_human_baseline_usd"),
        "cohens_kappa_rater1_rater2": agreement.get("cohens_kappa_rater1_rater2"),
        "cohens_kappa_clarity": agreement.get("cohens_kappa_clarity"),
        "judge_vs_majority_kappa": agreement.get("judge_vs_majority_kappa"),
        "krippendorff_alpha_nominal": agreement.get("krippendorff_alpha_nominal"),
        "fleiss_kappa_three_rater_items": agreement.get("fleiss_kappa_three_rater_items"),
        "approval_basis": result.approval_basis,
        "provider": result.provider_name,
    }
    return EvalReport(case.name, case.mode, tuple(outcomes), codes, metrics, broken)


def exit_code(reports: list[EvalReport], *, expect_red: bool) -> int:
    if any(report.broken or not report.safety_passed for report in reports):
        return EXIT_BROKEN
    quality_ok = all(report.quality_passed for report in reports)
    if expect_red:
        return EXIT_OK if quality_ok else EXIT_GATE_RED
    return EXIT_OK if quality_ok else EXIT_BROKEN


def format_report(reports: list[EvalReport], *, expect_red: bool, code: int) -> str:
    lines = ["100% synthetic; fictional domain.", "Invariant eval. Not a tool-call trajectory match."]
    for report in reports:
        lines.append(
            f"CASE {report.case_name} quality={report.quality_passed} "
            f"safety={report.safety_passed} codes={','.join(report.blocking_codes) or '-'}"
        )
        for outcome in report.outcomes:
            mark = "pass" if outcome.passed else "FAIL"
            lines.append(f"  [{outcome.kind}] {outcome.name}: {mark} — {outcome.detail}")
    if expect_red and code == EXIT_GATE_RED:
        lines.append("GATE_RED")
    elif code == EXIT_OK and not expect_red:
        lines.append("EVAL_PASS")
    elif code == EXIT_BROKEN:
        lines.append("GATE_BROKEN")
    else:
        lines.append("EVAL_UNEXPECTED")
    return "\n".join(lines) + "\n"
