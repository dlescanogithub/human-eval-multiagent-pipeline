"""Seeded agreement computation demo.

The raters are synthetic. The coefficients show that the metric functions run
on a panel large enough to move. They are not a measurement of human agreement.
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from pathlib import Path

from hemp.review.agreement import cohens_kappa, fleiss_kappa, krippendorff_alpha_nominal

PANEL_SIZE = 48
PANEL_SEED = 20261017
BOOTSTRAP_SEED = 20261018
N_BOOTSTRAP = 1000
CI_LOW_INDEX = 25
CI_HIGH_INDEX = 975

COMPUTATION_DISCLAIMER = (
    "COMPUTATION DEMO. Raters are synthetic. These numbers demonstrate the metric code. "
    "They are not real human agreement and this is not a human study."
)
IMPORT_DISCLAIMER = (
    "Imported labels. This command does not certify that the labels came from people "
    "and does not publish a real-agreement figure."
)

RATERS: tuple[tuple[str, float], ...] = (
    ("careful", 0.90),
    ("moderate", 0.75),
    ("noisy", 0.55),
)


@dataclass(frozen=True)
class RatedItem:
    item_id: str
    gold: str
    labels: dict[str, str]


def gold_for(index: int) -> str:
    """One fail in every four items, so both categories exist (12 fail / 36 pass at n=48)."""
    if index % 4 == 0:
        return "fail"
    return "pass"


def build_panel(n_items: int = PANEL_SIZE, seed: int = PANEL_SEED) -> list[RatedItem]:
    if n_items < 40:
        raise ValueError("the computation demo needs at least 40 items")
    rng = random.Random(seed)
    panel: list[RatedItem] = []
    for index in range(n_items):
        gold = gold_for(index)
        labels: dict[str, str] = {}
        for rater_id, design_rate in RATERS:
            if rng.random() < design_rate:
                labels[rater_id] = gold
            elif gold == "pass":
                labels[rater_id] = "fail"
            else:
                labels[rater_id] = "pass"
        panel.append(RatedItem(item_id=f"SYN-{index:03d}", gold=gold, labels=labels))
    return panel


def _column(items: list[RatedItem], rater_id: str) -> list[str]:
    return [item.labels[rater_id] for item in items]


def _point(items: list[RatedItem], kind: str) -> float:
    if kind == "cohens_kappa_careful_moderate":
        return cohens_kappa(_column(items, "careful"), _column(items, "moderate"))
    if kind == "cohens_kappa_careful_noisy":
        return cohens_kappa(_column(items, "careful"), _column(items, "noisy"))
    if kind == "cohens_kappa_moderate_noisy":
        return cohens_kappa(_column(items, "moderate"), _column(items, "noisy"))
    table = [_column_row(item) for item in items]
    if kind == "fleiss_kappa":
        return fleiss_kappa(table)
    if kind == "krippendorff_alpha_nominal":
        return krippendorff_alpha_nominal([[label for label in row] for row in table])
    raise ValueError(kind)


def _column_row(item: RatedItem) -> list[str]:
    return [item.labels[rater_id] for rater_id, _rate in RATERS]


def _bootstrap(items: list[RatedItem], kind: str, rng: random.Random) -> dict[str, float | int | str]:
    point = _point(items, kind)
    stats: list[float] = []
    count = len(items)
    for _ in range(N_BOOTSTRAP):
        sample = [items[rng.randrange(count)] for _ in range(count)]
        stats.append(_point(sample, kind))
    stats.sort()
    return {
        "point": point,
        "ci95_low": stats[CI_LOW_INDEX],
        "ci95_high": stats[CI_HIGH_INDEX],
        "n_bootstrap": N_BOOTSTRAP,
        "ci_low_index": CI_LOW_INDEX,
        "ci_high_index": CI_HIGH_INDEX,
        "method": "percentile bootstrap over items",
    }


def computation_demo(
    n_items: int = PANEL_SIZE,
    seed: int = PANEL_SEED,
    bootstrap_seed: int = BOOTSTRAP_SEED,
) -> dict[str, object]:
    panel = build_panel(n_items=n_items, seed=seed)
    rng = random.Random(bootstrap_seed)
    kinds = (
        "cohens_kappa_careful_moderate",
        "cohens_kappa_careful_noisy",
        "cohens_kappa_moderate_noisy",
        "fleiss_kappa",
        "krippendorff_alpha_nominal",
    )
    coefficients = {kind: _bootstrap(panel, kind, rng) for kind in kinds}
    realized: dict[str, float] = {}
    documented: list[dict[str, object]] = []
    for rater_id, design_rate in RATERS:
        matches = sum(item.labels[rater_id] == item.gold for item in panel) / len(panel)
        realized[rater_id] = matches
        documented.append(
            {
                "rater_id": rater_id,
                "design_match_rate": design_rate,
                "realized_match_rate": matches,
                "rule": "copy the seeded gold label with probability design_match_rate; otherwise flip it",
            }
        )
    return {
        "label": "synthetic",
        "status": "computation_demo",
        "disclaimer": COMPUTATION_DISCLAIMER,
        "not_a_human_study": True,
        "n_items": len(panel),
        "n_gold_fail": sum(item.gold == "fail" for item in panel),
        "n_gold_pass": sum(item.gold == "pass" for item in panel),
        "gold_rule": "fail when item index % 4 == 0, otherwise pass",
        "panel_seed": seed,
        "bootstrap_seed": bootstrap_seed,
        "raters": documented,
        "realized_match_rate": realized,
        "coefficients": coefficients,
    }


def format_computation_demo(report: dict[str, object]) -> str:
    lines = [
        "COMPUTATION DEMO — synthetic raters, not a human study",
        (f"n_items={report['n_items']} panel_seed={report['panel_seed']} bootstrap_seed={report['bootstrap_seed']}"),
        "Raters copy a seeded gold label at the design match rate, else they flip it.",
    ]
    raters = report["raters"]
    assert isinstance(raters, list)
    for rater in raters:
        assert isinstance(rater, dict)
        lines.append(
            f"- {rater['rater_id']}: design_match_rate={rater['design_match_rate']} "
            f"realized_match_rate={rater['realized_match_rate']}"
        )
    coefficients = report["coefficients"]
    assert isinstance(coefficients, dict)
    for name, payload in coefficients.items():
        assert isinstance(payload, dict)
        lines.append(f"{name}={payload['point']} ci95=[{payload['ci95_low']}, {payload['ci95_high']}]")
    lines.append(str(report["disclaimer"]))
    return "\n".join(lines)


def import_labels_csv(path: Path, *, bootstrap_seed: int = BOOTSTRAP_SEED) -> dict[str, object]:
    """Read item_id,rater_id,label. An empty template yields no coefficient."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError("CSV has no header") from exc
        expected = ["item_id", "rater_id", "label"]
        if [cell.strip() for cell in header] != expected:
            raise ValueError("CSV header must be item_id,rater_id,label")
        grouped: dict[str, dict[str, str]] = {}
        for row in reader:
            if not row or all(not cell.strip() for cell in row):
                continue
            if len(row) != 3:
                raise ValueError("each CSV row needs item_id,rater_id,label")
            item_id, rater_id, label = (cell.strip() for cell in row)
            if not item_id or not rater_id or not label:
                raise ValueError("item_id, rater_id, and label must be non-empty")
            slot = grouped.setdefault(item_id, {})
            if rater_id in slot:
                raise ValueError(f"duplicate label for {item_id} / {rater_id}")
            slot[rater_id] = label
    base: dict[str, object] = {
        "label": "imported",
        "disclaimer": IMPORT_DISCLAIMER,
        "not_a_human_study": True,
        "source": str(path),
    }
    if not grouped:
        base["status"] = "empty"
        base["n_items"] = 0
        base["n_raters"] = 0
        base["coefficients"] = None
        return base
    rater_ids = sorted({rater_id for labels in grouped.values() for rater_id in labels})
    rectangular = all(set(labels) == set(rater_ids) for labels in grouped.values())
    base["n_items"] = len(grouped)
    base["n_raters"] = len(rater_ids)
    base["rater_ids"] = rater_ids
    if not rectangular:
        base["status"] = "ragged"
        base["coefficients"] = None
        return base
    if len(grouped) < 2 or len(rater_ids) < 2:
        base["status"] = "too_small"
        base["coefficients"] = None
        return base
    item_ids = sorted(grouped)
    table = [[grouped[item_id][rater_id] for rater_id in rater_ids] for item_id in item_ids]
    rng = random.Random(bootstrap_seed)

    def point_of(sample: list[list[str]], kind: str) -> float:
        if kind == "cohen":
            return cohens_kappa([row[0] for row in sample], [row[1] for row in sample])
        if kind == "fleiss":
            return fleiss_kappa(sample)
        return krippendorff_alpha_nominal([[cell for cell in row] for row in sample])

    coefficients: dict[str, object] = {}
    for kind, key in (
        ("cohen", "cohens_kappa_first_two_raters"),
        ("fleiss", "fleiss_kappa"),
        ("krippendorff", "krippendorff_alpha_nominal"),
    ):
        stats: list[float] = []
        count = len(table)
        for _ in range(N_BOOTSTRAP):
            sample = [table[rng.randrange(count)] for _ in range(count)]
            stats.append(point_of(sample, kind))
        stats.sort()
        coefficients[key] = {
            "point": point_of(table, kind),
            "ci95_low": stats[CI_LOW_INDEX],
            "ci95_high": stats[CI_HIGH_INDEX],
            "n_bootstrap": N_BOOTSTRAP,
            "method": "percentile bootstrap over items",
        }
    base["status"] = "computed_from_import"
    base["coefficients"] = coefficients
    base["bootstrap_seed"] = bootstrap_seed
    base["cohen_rater_ids"] = rater_ids[:2]
    return base
