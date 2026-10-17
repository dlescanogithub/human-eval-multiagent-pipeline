from __future__ import annotations

from hemp.models import CostCard, QueueItem, Usage


def compute_cost(
    *,
    card: CostCard,
    usage: Usage,
    items: tuple[QueueItem, ...],
    attempted_lessons: int,
    cap_usd: float,
) -> dict[str, object]:
    """Dollar figures use the illustrative rate card. They are simulated, not a quote."""
    ai = usage.total / 1000.0 * card.ai_usd_per_1k_tokens
    reviews = sum(len(item.labels) for item in items)
    human_minutes = reviews * card.human_minutes_per_review
    human_usd = human_minutes / 60.0 * card.human_usd_per_hour
    total = ai + human_usd
    approved = sum(1 for item in items if item.status == "approved")
    baseline = attempted_lessons * card.all_human_minutes_per_lesson / 60.0 * card.human_usd_per_hour
    per_piece = (total / approved) if approved else None
    return {
        "label": "simulated",
        "estimate": True,
        "note": card.note,
        "ai_usd": round(ai, 6),
        "human_usd": round(human_usd, 6),
        "human_minutes": human_minutes,
        "total_usd": round(total, 6),
        "cap_usd": cap_usd,
        "within_cap": total <= cap_usd + 1e-9,
        "approved_pieces": approved,
        "attempted_lessons": attempted_lessons,
        "per_approved_piece_usd": None if per_piece is None else round(per_piece, 6),
        "all_human_baseline_usd": round(baseline, 6),
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
    }
