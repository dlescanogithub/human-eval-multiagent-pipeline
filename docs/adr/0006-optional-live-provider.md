# 0006 — The live provider stays off

## Status

Accepted. 2026-10-17. Revised the same day: `LIVE_LLM` replaces the earlier flag, and prices stay in the environment.

## Context

The default path replays writer, verifier, and critic steps from a cassette. That is what CI can test. A later run may want the same pipeline against an OpenAI-compatible chat-completions HTTP API. Turning that on by accident would spend money and send fictional lesson text off the machine.

## Decision

`python -m hemp live --pieces N` is the command that can open that connection. `make live` runs it with `--pieces 1`. It requires `LIVE_LLM=1`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, and `MAX_LIVE_SPEND_USD` greater than 0. Optional per-role models are `LLM_MODEL_WRITER`, `LLM_MODEL_VERIFIER`, and `LLM_MODEL_CRITIC`. Prices, if you have them, come only from `LLM_PRICE_IN_PER_MTOK` and `LLM_PRICE_OUT_PER_MTOK`. This repository does not store a vendor price. If both prices are unset, `MAX_LIVE_TOKENS` is required and cost is reported as unknown.

Anything missing exits 2, writes a JSON log, and does not call the network. The budget reserves the worst case before each call. When the cap is reached the process exits 3 with status `BUDGET_EXHAUSTED` and a partial report under gitignored `var/live-evals/`. Exit 3 is not a red gate. Retries cover 429, 5xx, and timeouts, with backoff, jitter, and `Retry-After`, and they stop at the cap. 401 and 403 are not retried. The API key is redacted in errors and logs. Demo, eval, and CI do not construct the live transport. No live result is written into the docs from this repository.

Corpus text and each role's output are passed to the next role as delimited data. An instruction embedded in a source document does not waive a citation. The forced regression includes a fake that obeys such an instruction; the checker still refuses to publish.

## Consequences

The pipeline shape is shared. The evidence in CI is still the cassette plus that local fake. Each live step's system prompt names the step, the input, and the JSON schema, and a schema miss retries at most twice inside the same spend cap. Cached prompt tokens are recorded and still priced as full input tokens, so the dollar figure overestimates a cache hit. A person who runs `hemp live` locally is responsible for the key and the spend cap. This repo's live-results table stays empty until someone measures a run and labels it. The live path is implementado, verificación live con un modelo real: pendiente. Real-model results: none yet. Cost per approved piece: not measured yet. judge-vs-human agreement: not measured yet.
