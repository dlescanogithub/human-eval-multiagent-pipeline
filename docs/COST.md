# Cost

Default run cost: **zero**. No API key, no network, no invoice. The dollars below are a conversion of measured token and review counts through an illustrative card. They are simulated.

Price date / source: the card is `fixtures/cost/illustrative_rates.json`, marked `estimate: true`, written for this repo on 2026-10-17. It is **not** taken from a vendor price page. Do not treat it as one.

| Scenario | Model / provider | Tokens or units | Cost / run | p50 / p95 latency | Quality | Price date / source |
| --- | --- | --- | --- | --- | --- | --- |
| Happy course, demo and eval | `fake-cassette-v1` (cassette) | 2550 prompt + 1550 completion tokens; 9 synthetic reviews; 72 human-minutes [EST] | 48.041 simulated USD (AI 0.041 + human 48). Cap 80. Per approved lesson 12.01025. All-human baseline 320 simulated USD | p50 2.414 ms / p95 2.454 ms, local, 21 runs, commit `COMMIT_SHA_HERE`, 2026-10-17. Not a vendor latency | 4/4 lessons approved; 17/17 invariants pass | [EST] card above. Tokens and review counts measured by `python -m hemp demo` |
| Repeat regression | same cassette style | AI only on the calls in that cassette; 2 reviews on the clean lesson | 10.692467 simulated USD, under cap | not separately timed | quality gate red; bad lesson not published | same [EST] card; figure from `python -m hemp eval-regression` on 2026-10-17 |
| Uncited regression | same | tokens only, no reviews (nothing queued) | 0.0182 simulated USD | not separately timed | quality gate red; nothing published | same |
| Optional live provider | not run. `python -m hemp live --pieces 1` exits 2 without `LIVE_LLM=1` and `MAX_LIVE_SPEND_USD` | not run | not measured yet | not run | not run | Off by default. Not used in CI. No vendor price is stored in the repo |

Rate card, all [EST]:

| Input | Value |
| --- | --- |
| AI | 0.01 simulated USD per 1k tokens |
| Reviewer time | 8 minutes per label |
| Reviewer rate | 40 simulated USD per hour |
| All-human lesson | 120 minutes |

Latency method: `run_case` on the happy `EvalCase`, 21 times, `time.perf_counter`, sorted, index `round(p * (n - 1))`. Warm process in this checkout, cassette already on disk. It does not include process startup of a cold `python -m hemp demo`. Measured 2026-10-17, package 0.1.2, commit `COMMIT_SHA_HERE`: p50 2.414 ms, p95 2.454 ms.

## Live mode

Cost per approved piece: **not measured yet**. No live run is claimed. Real-model results: none yet.

When both price variables are set in the environment, and only then:

`cost_usd = (tokens_in / 1_000_000) * LLM_PRICE_IN_PER_MTOK + (tokens_out / 1_000_000) * LLM_PRICE_OUT_PER_MTOK`

This repository does not store those prices. If both are unset, the run requires `MAX_LIVE_TOKENS` and the ledger records cost as `unknown`. `MAX_LIVE_SPEND_USD` is still required and must be greater than 0, or `python -m hemp live` exits 2 and does not call anyone.

Before each call the budget reserves the worst case: estimated input tokens (`max(1, len(body) // 4)`) plus `LLM_MAX_OUTPUT_TOKENS` (default 1024 when unset). After a 200 response it replaces that hold with reported usage. If the next reservation would pass the cap, the run stops before the call. If reported usage passes the cap after a call, the run stops after writing the ledger row. Exit code 3, status `BUDGET_EXHAUSTED`. That is not `GATE_RED` (exit 1) and not a config refusal (exit 2). The partial report lands in gitignored `var/live-evals/<stamp>/`. `python -m hemp live-summary --dir <that directory>` renders a one-page table for [LIVE_RUN_TEMPLATE.md](LIVE_RUN_TEMPLATE.md).
