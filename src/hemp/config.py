from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from hemp.errors import ConfigError


@dataclass(frozen=True)
class Policy:
    max_revisions: int = 3
    redundancy_jaccard_max: float = 0.55
    repetition_jaccard_max: float = 0.82
    repetition_min_tokens: int = 8
    groundedness_jaccard_min: float = 0.5
    uncertainty_threshold: float = 0.7
    base_reviews: int = 2
    uncertain_reviews: int = 3
    max_attempts: int = 3
    backoff_base_seconds: float = 0.05
    backoff_cap_seconds: float = 2.0
    cost_cap_simulated_usd: float = 80.0
    rater_seed: int = 101

    def with_max_revisions(self, max_revisions: int) -> Policy:
        return Policy(
            max_revisions=max_revisions,
            redundancy_jaccard_max=self.redundancy_jaccard_max,
            repetition_jaccard_max=self.repetition_jaccard_max,
            repetition_min_tokens=self.repetition_min_tokens,
            groundedness_jaccard_min=self.groundedness_jaccard_min,
            uncertainty_threshold=self.uncertainty_threshold,
            base_reviews=self.base_reviews,
            uncertain_reviews=self.uncertain_reviews,
            max_attempts=self.max_attempts,
            backoff_base_seconds=self.backoff_base_seconds,
            backoff_cap_seconds=self.backoff_cap_seconds,
            cost_cap_simulated_usd=self.cost_cap_simulated_usd,
            rater_seed=self.rater_seed,
        )


@dataclass(frozen=True)
class Settings:
    provider: str
    allow_network: bool
    log_level: str
    openai_api_key: str
    openai_base_url: str
    openai_model: str
    cost_cap_simulated_usd: float
    root: Path


def find_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").is_file() and (candidate / "fixtures").is_dir():
            return candidate
    raise ConfigError("repo root not found; run from a checkout with pyproject.toml and fixtures/")


def load_settings(
    environ: dict[str, str] | None = None,
    root: Path | None = None,
) -> Settings:
    env = os.environ if environ is None else environ
    provider = env.get("HEMP_PROVIDER", "cassette").strip().lower()
    if provider not in {"cassette", "openai"}:
        raise ConfigError(f"HEMP_PROVIDER must be cassette or openai, got {provider!r}")
    allow_network = env.get("HEMP_ALLOW_NETWORK", "0") == "1"
    cap_raw = env.get("HEMP_COST_CAP_USD", "80")
    try:
        cap = float(cap_raw)
    except ValueError as exc:
        raise ConfigError("HEMP_COST_CAP_USD must be a number") from exc
    if cap <= 0:
        raise ConfigError("HEMP_COST_CAP_USD must be positive")
    return Settings(
        provider=provider,
        allow_network=allow_network,
        log_level=env.get("HEMP_LOG_LEVEL", "INFO"),
        openai_api_key=env.get("OPENAI_API_KEY", ""),
        openai_base_url=env.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        openai_model=env.get("HEMP_MODEL", ""),
        cost_cap_simulated_usd=cap,
        root=root or find_root(),
    )
