# 0002 — No publish without the required reviews

## Status

Accepted. 2026-10-17.

## Context

A clean checker result is not the same as an editorial signature. The failure mode is a draft that looks finished and ships.

## Decision

`generate` enqueues accepted lessons as `pending` and approves nothing. Approval needs at least `required_raters` labels, safety at the rubric minimum on every label, and a mean at or above `min_pass` on every dimension. Critic confidence under 0.7 raises the count from 2 to 3. The demo may fill labels only if each one is `synthetic: true`.

## Consequences

The demo can finish offline, and the report has to say the approvals are synthetic. A real reviewer uses `review decide` or the local page and is stored with `synthetic: false`. There is still no notion of identity. That is a known limit, not a hidden feature.
