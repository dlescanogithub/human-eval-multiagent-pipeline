from __future__ import annotations

import re


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def jaccard(left: str, right: str) -> float:
    """Set Jaccard on word tokens. Both empty compares as identical."""
    a = set(tokenize(left))
    b = set(tokenize(right))
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def contains_term(text: str, term: str) -> bool:
    pattern = r"\b" + re.escape(term.lower()) + r"\b"
    return re.search(pattern, text.lower()) is not None


def sentences(text: str) -> tuple[str, ...]:
    parts = re.split(r"[.!?]+", text)
    return tuple(part.strip() for part in parts if part.strip())


def digest(text: str, n: int = 12) -> str:
    return " ".join(tokenize(text)[:n])
