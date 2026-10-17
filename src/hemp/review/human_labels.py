"""Judge-versus-human labels.

The committed template has an empty human_verdict column. This module does not
invent human labels. A synthetic fixture used only by tests is marked as such.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

from hemp.models import Corpus
from hemp.review.agreement import cohens_kappa

TEMPLATE_HEADER = ("piece_id", "claim", "source_excerpt", "human_verdict", "judge_verdict")
NOT_MEASURED = "judge-vs-human agreement: not measured yet"
N_BOOTSTRAP = 1000
CI_LOW_INDEX = 25
CI_HIGH_INDEX = 975


def export_template(corpus: Corpus, dest: Path, *, n: int, course_id: str) -> dict[str, object]:
    """Write n rows. human_verdict is empty. judge_verdict is the checker's expected label."""
    if n < 1:
        raise ValueError("n must be >= 1")
    if not corpus.facts:
        raise ValueError("corpus has no facts")
    dest.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for index in range(n):
        fact = corpus.facts[index % len(corpus.facts)]
        rows.append(
            {
                "piece_id": f"{course_id}:piece-{index + 1:02d}",
                "claim": fact.text,
                "source_excerpt": fact.text,
                "human_verdict": "",
                "judge_verdict": "pass",
            }
        )
    _write(dest, rows)
    return {"path": str(dest), "n": n, "human_verdicts_filled": 0, "note": NOT_MEASURED}


def judge_human_agreement(path: Path, *, bootstrap_seed: int = 20261017) -> dict[str, object]:
    """Cohen's kappa of judge_verdict vs human_verdict. Empty human cells are not a study."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or any(name not in reader.fieldnames for name in TEMPLATE_HEADER):
            raise ValueError("CSV header must include " + ",".join(TEMPLATE_HEADER))
        paired: list[tuple[str, str]] = []
        n_rows = 0
        for row in reader:
            n_rows += 1
            human = (row.get("human_verdict") or "").strip()
            judge = (row.get("judge_verdict") or "").strip()
            if not human:
                continue
            if not judge:
                raise ValueError("a filled human_verdict needs a judge_verdict")
            paired.append((judge, human))
    base: dict[str, object] = {
        "file": str(path),
        "n_rows": n_rows,
        "n": len(paired),
        "disclaimer": "Empty human_verdict cells are not labels. This command does not invent them.",
    }
    if len(paired) < 2:
        base["status"] = "not_measured"
        base["summary"] = NOT_MEASURED
        base["raw_agreement"] = None
        base["cohens_kappa"] = None
        return base
    judge = [item[0] for item in paired]
    human = [item[1] for item in paired]
    point = cohens_kappa(judge, human)
    raw = sum(left == right for left, right in paired) / len(paired)
    rng = random.Random(bootstrap_seed)
    stats: list[float] = []
    count = len(paired)
    for _ in range(N_BOOTSTRAP):
        sample = [paired[rng.randrange(count)] for _ in range(count)]
        stats.append(cohens_kappa([item[0] for item in sample], [item[1] for item in sample]))
    stats.sort()
    base["status"] = "computed"
    base["summary"] = f"n={len(paired)} raw_agreement={raw} cohens_kappa={point}"
    base["raw_agreement"] = raw
    base["cohens_kappa"] = {
        "point": point,
        "ci95_low": stats[CI_LOW_INDEX],
        "ci95_high": stats[CI_HIGH_INDEX],
        "n_bootstrap": N_BOOTSTRAP,
        "method": "percentile bootstrap over items",
    }
    return base


def _write(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(TEMPLATE_HEADER))
        writer.writeheader()
        writer.writerows(rows)
