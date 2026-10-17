# 0006 — The live provider stays off

## Status

Accepted. 2026-10-17.

## Context

The default path replays writer, verifier, and critic steps from a cassette. That is what CI can test. A later run may want the same pipeline against an OpenAI-compatible chat-completions HTTP API. Turning that on by accident would spend money and send fictional lesson text off the machine.

## Decision

`python -m hemp live` is the only command that can open that connection. It requires `LIVE_MODE=1` plus `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, `MAX_LIVE_SPEND_USD`, `LLM_PROMPT_USD_PER_1K`, `LLM_COMPLETION_USD_PER_1K`, and `LLM_PRICE_DATE`. Anything missing exits 2, writes a JSON log, and does not call the network. Retries are bounded, use exponential backoff with jitter, and honor `Retry-After` up to the backoff cap. Responses can be written as a cassette under gitignored `var/`. Demo, eval, and CI do not construct the live transport. No live result is written into the docs from this repository.

## Consequences

The pipeline shape is shared. The evidence in CI is still the cassette. A person who runs `hemp live` locally is responsible for the key, the spend cap, and the price date. This repo's tables leave the live-results rows empty until someone measures a run and labels it as such.
