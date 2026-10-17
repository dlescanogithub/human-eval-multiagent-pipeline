# 0001 — Cassette providers and invariant gates

## Status

Accepted. 2026-10-17.

## Context

The gate has to run in CI with no network and no paid API. Matching the exact list of model calls would break the moment a prompt is reworded, and it would not tell you whether a bad lesson was published.

## Decision

The default provider is an authored cassette. Evals call the checker again and assert properties: no uncited claim published, no external effect, summary matches accepted lessons, cost labeled simulated and under the cap, labels disclosed as synthetic. A separate command runs cassettes that repeat an earlier lesson or omit citations. That command must exit 1. CI fails if it does not.

## Consequences

The happy path is deterministic and free. A cassette can omit a step and the run errors, which is what we want. The gate does not prove that a live model would write the same JSON. The optional network adapter is outside the gate on purpose.
