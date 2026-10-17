# Cost

Default run cost: **zero**. No API key, no network, no invoice. The dollars below are a conversion of measured token and review counts through an illustrative card. They are simulated.

Price date / source: the card is `fixtures/cost/illustrative_rates.json`, marked `estimate: true`, written for this repo on 2026-10-17. It is **not** taken from a vendor price page. Do not treat it as one.

| Scenario | Model / provider | Tokens or units | Cost / run | p50 / p95 latency | Quality | Price date / source |
| --- | --- | --- | --- | --- | --- | --- |
| Happy course, demo and eval | `fake-cassette-v1` (cassette) | 2550 prompt + 1550 completion tokens; 9 synthetic reviews; 72 human-minutes [EST] | 48.041 simulated USD (AI 0.041 + human 48). Cap 80. Per approved lesson 12.01025. All-human baseline 320 simulated USD | p50 2.404 ms / p95 2.65 ms, local, 21 runs, commit `d8497e6`, 2026-10-17. Not a vendor latency | 4/4 lessons approved; 16/16 invariants pass | [EST] card above. Tokens and review counts measured by `python -m hemp demo` |
| Repeat regression | same cassette style | AI only on the calls in that cassette; 2 reviews on the clean lesson | 10.692467 simulated USD, under cap | not separately timed | quality gate red; bad lesson not published | same [EST] card; figure from `python -m hemp eval-regression` on 2026-10-17 |
| Uncited regression | same | tokens only, no reviews (nothing queued) | 0.0182 simulated USD | not separately timed | quality gate red; nothing published | same |
| Optional OpenAI-compatible adapter | whatever `HEMP_MODEL` points at | unknown until a real call | unknown; not run | not run | not run | off by default; CI does not call it |

Rate card, all [EST]:

| Input | Value |
| --- | --- |
| AI | 0.01 simulated USD per 1k tokens |
| Reviewer time | 8 minutes per label |
| Reviewer rate | 40 simulated USD per hour |
| All-human lesson | 120 minutes |

Latency method: `run_case` on the happy `EvalCase`, 21 times, `time.perf_counter`, sorted, index `round(p * (n - 1))`. Same machine as the agent, warm process, cassette already on disk. It does not include process startup of a cold `python -m hemp demo`.
