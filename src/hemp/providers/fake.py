from __future__ import annotations

from typing import Any

from hemp.errors import MissingCassetteError, TransientProviderError
from hemp.models import Usage
from hemp.providers.base import Completion, CompletionRequest


class FakeProvider:
    """In-memory provider for tests. Failures are explicit and transient only when asked."""

    name = "fake"

    def __init__(
        self,
        responses: dict[str, dict[str, Any]],
        *,
        fail_times: dict[str, int] | None = None,
        model: str = "fake-in-memory",
    ) -> None:
        self.responses = responses
        self.fail_times = dict(fail_times or {})
        self.model = model
        self.calls: list[str] = []

    def complete(self, request: CompletionRequest) -> Completion:
        self.calls.append(request.key)
        remaining = self.fail_times.get(request.key, 0)
        if remaining > 0:
            self.fail_times[request.key] = remaining - 1
            raise TransientProviderError(request.key)
        if request.key not in self.responses:
            raise MissingCassetteError(request.key)
        return Completion(
            content=self.responses[request.key],
            usage=Usage(1, 1),
            provider=self.name,
            model=self.model,
        )
