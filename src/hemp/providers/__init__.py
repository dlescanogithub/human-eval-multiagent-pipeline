"""Providers. The default is a cassette. The live chat-completions provider is off."""

from pathlib import Path

from hemp.errors import ConfigError
from hemp.providers.base import Completion, CompletionRequest
from hemp.providers.cassette import CassetteProvider
from hemp.providers.fake import FakeProvider
from hemp.providers.llm_openai_compatible import LlmOpenAICompatible, parse_chat_response
from hemp.providers.retry import RetryingProvider

__all__ = [
    "CassetteProvider",
    "Completion",
    "CompletionRequest",
    "FakeProvider",
    "LlmOpenAICompatible",
    "RetryingProvider",
    "build_provider",
    "parse_chat_response",
]


def build_provider(
    *,
    provider: str,
    allow_network: bool,
    api_key: str,
    base_url: str,
    model: str,
    cassette_path: str,
) -> CassetteProvider:
    """Cassette lookup only. Live calls go through ``python -m hemp live``."""
    del api_key, base_url, model
    if provider != "cassette" or allow_network:
        raise ConfigError("Live calls are off. Set LIVE_LLM=1 outside CI and use python -m hemp live.")
    if not cassette_path:
        raise ConfigError("cassette_path is required")
    return CassetteProvider.load(Path(cassette_path))
