# 0005 — The running summary is explicit state

## Status

Accepted. 2026-10-17.

## Context

Lesson 2 should not rediscover lesson 1 by accident. Hiding "what we already covered" inside a long prompt makes the redundancy check unreproducible.

## Decision

`RunningSummary` holds accepted lesson ids, topics, objective ids, and a short digest. It is passed on the writer request and copied onto the trace. Only an accepted lesson updates it. The safety invariant checks that the summary's ids equal the accepted ids, in order, and that each writer request saw the summary of what had been accepted so far.

## Consequences

A rejected lesson cannot become the baseline for the next one. The cassette is keyed by step id, not by hashing the summary, so the summary is recorded rather than used as a cache key. A live model would still need the summary in the prompt; the cassette ignores the payload and returns the authored step. That is acceptable for the offline gate and is called out in ADR 0001.
