from __future__ import annotations

from hemp.config import Policy


def required_raters(confidence: float, policy: Policy) -> int:
    """Low judge confidence asks for one extra rater. Confidence is the critic's, not a human's."""
    if confidence < policy.uncertainty_threshold:
        return policy.uncertain_reviews
    return policy.base_reviews
