from __future__ import annotations


def drift_report(
    weeks: tuple[tuple[str, tuple[float, ...]], ...],
    *,
    threshold: float,
    disclaimer: str,
    baseline_weeks: int = 2,
) -> dict[str, object]:
    """Compare later simulated weeks with the mean of the first weeks.

    Alerts are computed from rounded means so a reader can recompute them from the report.
    """
    if baseline_weeks < 1 or baseline_weeks >= len(weeks):
        raise ValueError("baseline_weeks must leave at least one later week")
    means = [round(sum(scores) / len(scores), 6) for _, scores in weeks]
    baseline = round(sum(means[:baseline_weeks]) / baseline_weeks, 6)
    rows: list[dict[str, object]] = []
    alerts: list[str] = []
    for index, ((name, _), mean) in enumerate(zip(weeks, means, strict=True)):
        alert = index >= baseline_weeks and abs(mean - baseline) >= threshold
        if alert:
            alerts.append(name)
        rows.append({"week": name, "mean": mean, "alert": alert})
    return {
        "label": "simulated",
        "disclaimer": disclaimer,
        "threshold": threshold,
        "baseline_weeks": baseline_weeks,
        "baseline_mean": baseline,
        "weeks": rows,
        "alert_weeks": alerts,
    }
