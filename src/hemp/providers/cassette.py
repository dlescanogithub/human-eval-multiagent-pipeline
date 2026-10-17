from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hemp.errors import MissingCassetteError, SchemaError
from hemp.load import parse_usage, read_json
from hemp.models import Usage
from hemp.providers.base import Completion, CompletionRequest


@dataclass(frozen=True)
class StoredStep:
    content: dict[str, Any]
    usage_prompt: int
    usage_completion: int


class CassetteProvider:
    """Lookup table of authored responses. This is not a recording of a vendor call."""

    name = "cassette"

    def __init__(self, steps: dict[str, StoredStep], *, model: str, notes: str) -> None:
        self.steps = steps
        self.model = model
        self.notes = notes

    @classmethod
    def load(cls, path: Path) -> CassetteProvider:
        data = read_json(path)
        if not isinstance(data, dict):
            raise SchemaError("cassette must be an object")
        raw_steps = data.get("steps")
        if not isinstance(raw_steps, dict) or not raw_steps:
            raise SchemaError("cassette steps must be a non-empty object")
        steps: dict[str, StoredStep] = {}
        for key, value in raw_steps.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                raise SchemaError("each cassette step must be an object")
            content = value.get("content")
            if not isinstance(content, dict):
                raise SchemaError(f"{key} content must be an object")
            usage = parse_usage(value)
            steps[key] = StoredStep(content, usage.prompt_tokens, usage.completion_tokens)
        model = data.get("model", "fake-cassette-v1")
        if not isinstance(model, str):
            raise SchemaError("model must be a string")
        notes = data.get("notes", "")
        if not isinstance(notes, str):
            raise SchemaError("notes must be a string")
        return cls(steps, model=model, notes=notes)

    def complete(self, request: CompletionRequest) -> Completion:
        stored = self.steps.get(request.key)
        if stored is None:
            raise MissingCassetteError(request.key)
        return Completion(
            content=stored.content,
            usage=Usage(stored.usage_prompt, stored.usage_completion),
            provider=self.name,
            model=self.model,
        )
