# Changelog

## Unreleased

- Add narrated English demo video (`human_eval_multiagent_pipeline_demo_en.mp4`) with subtitles and evidence pack under `docs/demo/`.
- Removed interview framing. [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) is a walkthrough for engineers and buyers, and the README docs list no longer calls it an interview walkthrough. A repo-wide search found no Spanish prose. The pending IP checklist in [docs/IP_AND_PROVENANCE.md](docs/IP_AND_PROVENANCE.md) is unchanged and still open. No code change.
- README is English only. Added [docs/BUSINESS_VALUE.md](docs/BUSINESS_VALUE.md). [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) is in English and matches the current tree. The pending IP checklist in [docs/IP_AND_PROVENANCE.md](docs/IP_AND_PROVENANCE.md) is unchanged and still open. No code change.
- Pytest re-measured on 2026-10-22, Python 3.12.3, pytest 9.1.1, package 0.1.3, code at `228dd93981cc1805d627d7b6f1248caa999618de`: 67 passed, line coverage 89.06%. Command `python -m pytest --cov=hemp --cov-report=term-missing --cov-report=json:coverage.json`, with the project floor of 80%. Same totals as the 2026-10-17 line. pytest-cov printed that module hemp was previously imported and not measured. The 89.06% figure is the total it printed.
- Docs record two independent live runs from 2026-10-17, xAI `grok-4.20-0309-non-reasoning`, `LIVE_LLM` set to 1, `MAX_LIVE_SPEND_USD` set to 0.15. `python -m hemp live --pieces 1`: exit 0, 7 calls, checker accepted 1/1, pending, published 0, live result not claimed, real 0.00785 USD, repo estimate 0.00879 USD. `python -m hemp live --pieces 3`: exit 0, 25 calls, checker accepted 1/3, 0 parse or format retries, real 0.03416 USD, repo estimate 0.03994 USD. Live was run at n=1 and n=3, a small sample, with no rate. judge-vs-human agreement: not measured yet. No code change.

## 0.1.3 — 2026-10-17

- Each live step (outline, writer, verifier, critic) names itself, its input, and the exact JSON object to return, with a minimal example, and asks for only that JSON.
- A bad object is extracted from a ```json fence when one is present, rejected with an actionable schema error, and retried at most twice. Each retry reserves the worst case against the spend cap before the call. A lesson object where an outline was required says that the lessons list is missing.
- Reported cached prompt tokens are stored on the ledger. The live cost formula still prices every prompt token at `LLM_PRICE_IN_PER_MTOK`, so a cache hit is an overestimate. No cached price is stored.
- The live path is implemented. A live check against a real model was still pending in this release. Real-model results: none yet. Cost per approved piece: not measured yet.

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
