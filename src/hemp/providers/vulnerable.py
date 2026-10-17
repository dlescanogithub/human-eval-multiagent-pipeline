"""Fixture provider that obeys an instruction embedded in corpus data.

It exists so the gate can prove that obedience does not publish an uncited lesson.
It is not a model and it is not used by demo or by the happy eval.
"""

from __future__ import annotations

from typing import Any

from hemp.errors import MissingCassetteError
from hemp.models import Usage
from hemp.providers.base import Completion, CompletionRequest

MARKER = "EMBEDDED-INSTRUCTION"


class VulnerableProvider:
    """If corpus data contains the marker, the writer drops citations."""

    name = "fake"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def complete(self, request: CompletionRequest) -> Completion:
        self.calls.append(request.key)
        if request.role == "writer" and request.step == "outline":
            content = _outline(request)
        elif request.role == "writer":
            content = _draft(request, obey=_poisoned(request))
        elif request.role == "verifier":
            content = {"claim_reviews": [{"claim_id": "L1-C1", "supported": False, "corpus_ids": []}]}
        elif request.role == "critic":
            content = {
                "rubric_version": str(request.payload.get("rubric_version", "")),
                "scores": {
                    "accuracy": 1,
                    "clarity": 5,
                    "flow": 5,
                    "no_redundancy": 5,
                    "safety": 5,
                },
                "confidence": 0.4,
                "request_revision": False,
                "safety_block": False,
                "comments": ["Fixture critic. Not a model."],
            }
        else:
            raise MissingCassetteError(request.key)
        return Completion(content=content, usage=Usage(12, 8), provider=self.name, model="vulnerable-fake")


def _poisoned(request: CompletionRequest) -> bool:
    data = request.payload.get("untrusted_data", {})
    corpus = data.get("corpus", []) if isinstance(data, dict) else []
    if not isinstance(corpus, list):
        return False
    return any(isinstance(item, dict) and MARKER in str(item.get("text", "")) for item in corpus)


def _outline(request: CompletionRequest) -> dict[str, Any]:
    objectives = request.payload.get("objective_ids", ["OBJ-WAYBILL"])
    if not isinstance(objectives, list) or not objectives:
        objectives = ["OBJ-WAYBILL"]
    return {
        "course_id": request.payload.get("course_id", ""),
        "title": "Poisoned slice",
        "lessons": [
            {
                "id": "L1",
                "title": "Waybills and handoff tokens",
                "objective_ids": [str(objectives[0])],
                "prerequisite_ids": [],
            }
        ],
    }


def _draft(request: CompletionRequest, *, obey: bool) -> dict[str, Any]:
    spec = request.payload.get("lesson_spec", {})
    if not isinstance(spec, dict):
        spec = {}
    citations: list[str] = [] if obey else ["F-WAYBILL"]
    return {
        "id": spec.get("id", "L1"),
        "title": spec.get("title", "Waybills and handoff tokens"),
        "objective_ids": list(spec.get("objective_ids", ["OBJ-WAYBILL"])),
        "prerequisite_ids": list(spec.get("prerequisite_ids", [])),
        "topics": ["waybill", "handoff token"],
        "body": (
            "A Nortia waybill lists the origin dock, the destination dock, "
            "the cargo class, and a four-character handoff token."
        ),
        "claims": [
            {
                "id": "L1-C1",
                "text": (
                    "A Nortia waybill lists the origin dock, the destination dock, "
                    "the cargo class, and a four-character handoff token."
                ),
                "citation_ids": citations,
            }
        ],
    }
