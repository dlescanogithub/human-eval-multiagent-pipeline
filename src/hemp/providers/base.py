from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from hemp.models import Usage


@dataclass(frozen=True)
class CompletionRequest:
    role: str
    step: str
    payload: dict[str, Any]

    @property
    def key(self) -> str:
        return f"{self.role}:{self.step}"


@dataclass(frozen=True)
class Completion:
    content: dict[str, Any]
    usage: Usage
    provider: str
    model: str


class Provider(Protocol):
    name: str

    def complete(self, request: CompletionRequest) -> Completion:
        """Return a structured completion. Must not be called against a paid API in CI."""
