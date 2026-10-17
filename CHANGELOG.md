# Changelog

## 0.1.2 — 2026-10-17

- Optional live provider `llm_openai_compatible` for an OpenAI-compatible chat-completions API. Off unless `LIVE_LLM=1` and `MAX_LIVE_SPEND_USD` is greater than 0. Exit 2 without that config. Exit 3 (`BUDGET_EXHAUSTED`) when the spend or token cap is hit. Prices come only from the environment. No live result is claimed. Cost per approved piece: not measured yet.
- Corpus text and prior role output are delimited as data. A poisoned-document regression uses a fake that obeys an embedded instruction; the checker still refuses to publish and the forced regression exits 1 with `GATE_RED`.
- `python -m hemp review export --n 30` writes `labels/human_labels.template.csv` with an empty `human_verdict`. `review agreement` reports judge-vs-human agreement: not measured yet. No invented labels.
- `secretscan.py` sha256 recorded in `docs/PROVENANCE.md`.

## 0.1.1 — 2026-10-17

- Secret scanner covers the shared token shapes. `docs/PROVENANCE.md` records the sha256 of `src/hemp/secretscan.py`.
- Agreement computation demo: 48 synthetic items, three seeded reliabilities, bootstrap intervals over items. CSV import plus an empty template. No human-agreement figure.
- Optional live provider for an OpenAI-compatible chat-completions API, gated by `LIVE_MODE` in this release. Superseded in 0.1.2 by `LIVE_LLM`, an environment-only price, and exit 3 on budget exhaustion. No live result is claimed.
- Docs call this a multi-step cassette pipeline. The repository name is unchanged.

## 0.1.0 — 2026-10-17

Initial private portfolio slice.

- Synthetic course for the fictional company Nortia Learning.
- Cassette pipeline: outline, running summary, writer, verifier, critic, bounded revisions.
- Deterministic checker and invariant gate, including a regression that is required to fail.
- File, CLI, and local review queue. Agreement metrics on seeded synthetic labels.
- No runtime dependencies. CI does not call a paid API.
