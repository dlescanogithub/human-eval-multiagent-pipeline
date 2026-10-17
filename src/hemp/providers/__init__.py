"""Providers. The default is a cassette. The live chat-completions provider is off."""

from hemp.providers.base import Completion, CompletionRequest
from hemp.providers.cassette import CassetteProvider
from hemp.providers.fake import FakeProvider
from hemp.providers.openai_compat import OpenAICompatProvider, build_provider, parse_chat_response
from hemp.providers.retry import RetryingProvider

__all__ = [
    "CassetteProvider",
    "Completion",
    "CompletionRequest",
    "FakeProvider",
    "OpenAICompatProvider",
    "RetryingProvider",
    "build_provider",
    "parse_chat_response",
]
