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
class LiveConfig:
    """Settings for one optional live run. Absent unless ``load_live_config`` succeeds."""

    base_url: str
    api_key: str
    model: str
    model_writer: str
    model_verifier: str
    model_critic: str
    max_output_tokens: int
    timeout_s: float
    max_spend_usd: float
    price_in_per_mtok: float | None
    price_out_per_mtok: float | None
    max_live_tokens: int | None

    def model_for(self, role: str) -> str:
        if role == "writer":
            return self.model_writer
        if role == "verifier":
            return self.model_verifier
        if role == "critic":
            return self.model_critic
        return self.model

    @property
    def prices_known(self) -> bool:
        return self.price_in_per_mtok is not None and self.price_out_per_mtok is not None


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


def _optional_float(env: dict[str, str], name: str) -> float | None:
    raw = env.get(name, "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number") from exc


def _optional_int(env: dict[str, str], name: str) -> int | None:
    raw = env.get(name, "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc
    return value


def load_live_config(environ: dict[str, str] | None = None) -> LiveConfig:
    """Closed door. Demo and eval do not call this.

    ``LIVE_LLM=1`` and ``MAX_LIVE_SPEND_USD`` (> 0) are required. Prices come only
    from the environment. When they are unset, ``MAX_LIVE_TOKENS`` is required and
    cost is reported as unknown.
    """
    env = dict(os.environ if environ is None else environ)
    if env.get("LIVE_LLM", "0") != "1":
        raise ConfigError("LIVE_LLM is not 1; the live provider is off")
    missing = [
        name
        for name in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL", "MAX_LIVE_SPEND_USD")
        if not env.get(name, "").strip()
    ]
    if missing:
        raise ConfigError("live config missing: " + ",".join(missing))
    try:
        max_spend = float(env["MAX_LIVE_SPEND_USD"])
    except ValueError as exc:
        raise ConfigError("MAX_LIVE_SPEND_USD must be a number") from exc
    if max_spend <= 0:
        raise ConfigError("MAX_LIVE_SPEND_USD must be > 0")
    price_in = _optional_float(env, "LLM_PRICE_IN_PER_MTOK")
    price_out = _optional_float(env, "LLM_PRICE_OUT_PER_MTOK")
    if (price_in is None) != (price_out is None):
        raise ConfigError("set both LLM_PRICE_IN_PER_MTOK and LLM_PRICE_OUT_PER_MTOK, or neither")
    if price_in is not None and (price_in < 0 or price_out is None or price_out < 0):
        raise ConfigError("live prices must be non-negative")
    max_tokens = _optional_int(env, "MAX_LIVE_TOKENS")
    if price_in is None and (max_tokens is None or max_tokens <= 0):
        raise ConfigError("MAX_LIVE_TOKENS is required and must be > 0 when live prices are unset")
    if max_tokens is not None and max_tokens <= 0:
        raise ConfigError("MAX_LIVE_TOKENS must be > 0")
    max_output = _optional_int(env, "LLM_MAX_OUTPUT_TOKENS") or 1024
    if max_output <= 0:
        raise ConfigError("LLM_MAX_OUTPUT_TOKENS must be > 0")
    timeout_raw = env.get("LLM_TIMEOUT_S", "").strip()
    timeout_s = 30.0
    if timeout_raw:
        try:
            timeout_s = float(timeout_raw)
        except ValueError as exc:
            raise ConfigError("LLM_TIMEOUT_S must be a number") from exc
    if timeout_s <= 0:
        raise ConfigError("LLM_TIMEOUT_S must be > 0")
    model = env["LLM_MODEL"].strip()
    return LiveConfig(
        base_url=env["LLM_BASE_URL"].strip(),
        api_key=env["LLM_API_KEY"].strip(),
        model=model,
        model_writer=env.get("LLM_MODEL_WRITER", "").strip() or model,
        model_verifier=env.get("LLM_MODEL_VERIFIER", "").strip() or model,
        model_critic=env.get("LLM_MODEL_CRITIC", "").strip() or model,
        max_output_tokens=max_output,
        timeout_s=timeout_s,
        max_spend_usd=max_spend,
        price_in_per_mtok=price_in,
        price_out_per_mtok=price_out,
        max_live_tokens=max_tokens,
    )
