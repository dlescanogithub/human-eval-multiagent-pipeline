from __future__ import annotations

from collections.abc import Callable

from hemp.config import Policy
from hemp.errors import TransientProviderError
from hemp.providers.base import Completion, CompletionRequest, Provider


class RetryingProvider:
    """Bounded retries for transient failures. The cap is ``policy.backoff_cap_seconds``."""

    def __init__(
        self,
        inner: Provider,
        policy: Policy,
        *,
        sleep: Callable[[float], None] = lambda _seconds: None,
    ) -> None:
        self.inner = inner
        self.policy = policy
        self.sleep = sleep
        self.attempts: list[str] = []
        self.name = inner.name

    def complete(self, request: CompletionRequest) -> Completion:
        delay = self.policy.backoff_base_seconds
        last: TransientProviderError | None = None
        for attempt in range(1, self.policy.max_attempts + 1):
            self.attempts.append(f"{request.key}#{attempt}")
            try:
                return self.inner.complete(request)
            except TransientProviderError as exc:
                last = exc
                if attempt >= self.policy.max_attempts:
                    break
                self.sleep(min(self.policy.backoff_cap_seconds, delay))
                delay = min(self.policy.backoff_cap_seconds, delay * 2)
        assert last is not None
        raise last
