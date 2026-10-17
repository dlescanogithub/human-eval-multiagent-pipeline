from __future__ import annotations

from hemp.models import QueueItem


def cohens_kappa(left: list[str], right: list[str]) -> float:
    """Cohen's kappa for two raters. Returns 1 when there is only one observed category."""
    if len(left) != len(right) or not left:
        raise ValueError("kappa needs two equal non-empty rating lists")
    count = len(left)
    labels = sorted(set(left) | set(right))
    observed = sum(a == b for a, b in zip(left, right, strict=True)) / count
    expected = 0.0
    for label in labels:
        expected += (left.count(label) / count) * (right.count(label) / count)
    if expected == 1.0:
        return 1.0
    return (observed - expected) / (1.0 - expected)


def fleiss_kappa(ratings: list[list[str]]) -> float:
    """Fleiss' kappa. ``ratings`` is a rectangular items-by-raters table with at least two raters."""
    if not ratings:
        raise ValueError("fleiss needs items")
    raters = len(ratings[0])
    if raters < 2 or any(len(item) != raters for item in ratings):
        raise ValueError("fleiss needs a rectangular table with at least 2 raters")
    categories = sorted({value for item in ratings for value in item})
    n_items = len(ratings)
    item_agreement: list[float] = []
    for item in ratings:
        counts = [item.count(category) for category in categories]
        squares = sum(count * count for count in counts)
        item_agreement.append((squares - raters) / (raters * (raters - 1)))
    proportions: list[float] = []
    for category in categories:
        total = sum(item.count(category) for item in ratings)
        proportions.append(total / (n_items * raters))
    observed = sum(item_agreement) / n_items
    expected = sum(value * value for value in proportions)
    if expected == 1.0:
        return 1.0
    return (observed - expected) / (1.0 - expected)


def krippendorff_alpha_nominal(units: list[list[str | None]]) -> float:
    """Nominal Krippendorff's alpha. ``None`` marks a missing rater. Coincidence-matrix form."""
    categories = sorted({value for unit in units for value in unit if value is not None})
    if not categories:
        raise ValueError("alpha needs observed values")
    index = {category: position for position, category in enumerate(categories)}
    size = len(categories)
    coincidence = [[0.0 for _ in range(size)] for _ in range(size)]
    for unit in units:
        values = [value for value in unit if value is not None]
        observed = len(values)
        if observed < 2:
            continue
        for row in range(observed):
            for column in range(observed):
                if row == column:
                    continue
                left = index[values[row]]
                right = index[values[column]]
                coincidence[left][right] += 1.0 / (observed - 1)
    pairs = sum(sum(row) for row in coincidence)
    if pairs <= 1:
        raise ValueError("alpha needs at least one pair")
    disagreement = 0.0
    for row in range(size):
        for column in range(size):
            if row != column:
                disagreement += coincidence[row][column]
    observed_disagreement = disagreement / pairs
    marginals = [sum(coincidence[row][column] for column in range(size)) for row in range(size)]
    expected = 0.0
    for row in range(size):
        for column in range(size):
            if row != column:
                expected += marginals[row] * marginals[column]
    expected_disagreement = expected / (pairs * (pairs - 1))
    if expected_disagreement == 0.0:
        return 1.0
    return 1.0 - (observed_disagreement / expected_disagreement)


def overall_label(scores: dict[str, int], mins: dict[str, int]) -> str:
    if all(scores[dimension] >= minimum for dimension, minimum in mins.items()):
        return "pass"
    return "fail"


def agreement_report(items: tuple[QueueItem, ...], mins: dict[str, int]) -> dict[str, object]:
    """Agreement on synthetic labels. The disclaimer is part of the result on purpose."""
    disclaimer = (
        "Synthetic rater labels from a seeded function on the 4-lesson course fixture. "
        "This n is too small to interpret. Not a human calibration study. "
        "The computation demo lives in agreement_demo.py."
    )
    if not items:
        return {"label": "synthetic", "status": "not_applicable", "disclaimer": disclaimer}
    if any(len(item.labels) < 2 for item in items):
        return {
            "label": "synthetic",
            "status": "incomplete",
            "disclaimer": disclaimer,
            "n_items": len(items),
        }
    rater_one: list[str] = []
    rater_two: list[str] = []
    judge: list[str] = []
    majority: list[str] = []
    matrix: list[list[str | None]] = []
    three_rater: list[list[str]] = []
    for item in items:
        labels = item.labels
        first = overall_label(labels[0].scores, mins)
        second = overall_label(labels[1].scores, mins)
        rater_one.append(first)
        rater_two.append(second)
        judge.append(overall_label(item.judge_scores, mins))
        decisions = [overall_label(label.scores, mins) for label in labels]
        passes = decisions.count("pass")
        majority.append("pass" if passes > len(decisions) - passes else "fail")
        row: list[str | None] = [first, second]
        if len(labels) >= 3:
            row.append(decisions[2])
            three_rater.append(decisions[:3])
        else:
            row.append(None)
        matrix.append(row)
    report: dict[str, object] = {
        "label": "synthetic",
        "status": "computed",
        "disclaimer": disclaimer,
        "n_items": len(items),
        "cohens_kappa_rater1_rater2": cohens_kappa(rater_one, rater_two),
        "cohens_kappa_clarity": cohens_kappa(
            [str(item.labels[0].scores["clarity"]) for item in items],
            [str(item.labels[1].scores["clarity"]) for item in items],
        ),
        "judge_vs_rater2_kappa": cohens_kappa(judge, rater_two),
        "judge_vs_majority_kappa": cohens_kappa(judge, majority),
        "krippendorff_alpha_nominal": krippendorff_alpha_nominal(matrix),
        "rubric_version": items[0].rubric_version,
    }
    if three_rater:
        report["fleiss_kappa_three_rater_items"] = fleiss_kappa(three_rater)
        report["fleiss_n_items"] = len(three_rater)
    else:
        report["fleiss_kappa_three_rater_items"] = None
        report["fleiss_n_items"] = 0
    return report
