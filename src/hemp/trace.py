from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class TraceLog:
    """Append-only JSONL trace. Every row carries the rubric version."""

    def __init__(
        self,
        *,
        rubric_version: str,
        clock: Callable[[], str] | None = None,
        path: Path | None = None,
    ) -> None:
        self.rubric_version = rubric_version
        self.clock = clock or utc_now
        self.path = path
        self.events: list[dict[str, Any]] = []
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")

    def add(self, event: str, **fields: Any) -> dict[str, Any]:
        row: dict[str, Any] = {
            "event": event,
            "ts": self.clock(),
            "rubric_version": self.rubric_version,
        }
        row.update(fields)
        self.events.append(row)
        if self.path is not None:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
        return row
