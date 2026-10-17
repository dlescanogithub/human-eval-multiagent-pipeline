# Changelog

## 0.1.1 — 2026-10-17

- Secret scanner covers the shared token shapes. `docs/PROVENANCE.md` records the sha256 of `src/hemp/secretscan.py`.
- Agreement computation demo: 48 synthetic items, three seeded reliabilities, bootstrap intervals over items. CSV import plus an empty template. No human-agreement figure.
- Optional live provider for an OpenAI-compatible chat-completions API. Off unless `LIVE_MODE=1` and the live settings are present. Exit 2 without that config. Cassettes land in gitignored `var/`. No live result is claimed.
- Docs call this a multi-step cassette pipeline. The repository name is unchanged.

## 0.1.0 — 2026-10-17

Initial private portfolio slice.

- Synthetic course for the fictional company Nortia Learning.
- Cassette pipeline: outline, running summary, writer, verifier, critic, bounded revisions.
- Deterministic checker and invariant gate, including a regression that is required to fail.
- File, CLI, and local review queue. Agreement metrics on seeded synthetic labels.
- No runtime dependencies. CI does not call a paid API.
