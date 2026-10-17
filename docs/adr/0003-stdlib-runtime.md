# 0003 — Standard-library runtime

## Status

Accepted. 2026-10-17.

## Context

The exercise has to install, lint, typecheck, and test without a vendor SDK. Extra libraries would need supply-chain review for very little gain at this size.

## Decision

`pyproject.toml` has no runtime dependencies. JSON, HTTP for the local page, and `urllib` for the optional adapter are from the standard library. Dev tools (pytest, ruff, mypy, pre-commit) are extras.

## Consequences

The Docker image is a single `pip install` of this package. The local page is plain HTML with no frontend build. mypy strict is practical because the surface is small. A future vector store or a real UI would be a new decision, not a quiet dependency.
