from __future__ import annotations

import random

from hemp.config import Policy
from hemp.models import QueueItem, ReviewLabel
from hemp.review.queue import decide


def synthesize_item(
    item: QueueItem,
    *,
    ordinal: int,
    policy: Policy,
    mins: dict[str, int],
) -> QueueItem:
    """Seeded synthetic labels.

    The pattern is a pure function of ``policy.rater_seed``, the lesson ordinal, and the rater
    index. It keeps every score inside the publish band. Clarity is lowered on the first lesson
    for every rater and on the second lesson for rater 2 only, so pairwise clarity kappa is not
    1. Safety is copied from the judge. This is not a sample of human raters.
    """
    labels: list[ReviewLabel] = []
    for rater_index in range(item.required_raters):
        rng = random.Random(policy.rater_seed + ordinal * 100 + rater_index)
        scores = dict(item.judge_scores)
        if ordinal == 0 or (ordinal == 1 and rater_index == 1):
            scores["clarity"] = min(5, max(1, item.judge_scores["clarity"] - 1))
        else:
            scores["flow"] = min(5, max(1, scores["flow"] + rng.choice((0, 0, 0, -1))))
        if ordinal == 3 and rater_index == 2:
            scores["flow"] = min(5, max(1, item.judge_scores["flow"] - 1))
        scores["safety"] = item.judge_scores["safety"]
        labels.append(
            ReviewLabel(
                rater_id=f"synthetic-rater-{rater_index + 1}",
                scores=scores,
                synthetic=True,
            )
        )
    pending = item.with_labels(tuple(labels), "pending")
    return decide(pending, mins)
