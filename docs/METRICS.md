# Metrics

Success, for this repo, means the gate can go green on a clean course and red on a bad one, with a trace a person can read. It does not mean a business outcome was observed.

## Measured (2026-10-17, package 0.1.3, commit `ccafba8048f54f825c77af89744895f0c7f0c659`)

| Metric | Value | Command |
| --- | --- | --- |
| Tests | 67 passed | `python -m pytest` (pytest 9.1.1, Python 3.12.3) |
| Line coverage | 89.06% | same command, floor 80% in `pyproject.toml` |
| Happy gate | `EVAL_PASS`, 17/17 invariants (10 safety, 7 quality) | `python -m hemp eval` |
| Regression gate | exit 1, `GATE_RED` | `python -m hemp eval-regression` |
| Happy lessons approved | 4/4 | `python -m hemp demo` |
| Revision used | L2 writer_calls = 2 | same |
| Adaptive raters | L4 required_raters = 3; others 2 | same |
| Agreement computation demo | 48 synthetic items; careful/moderate Cohen 0.383399, 95% interval 0.120690 to 0.667984 | `python -m hemp agreement-demo` (seeds 20261017 and 20261018). Not a human study |
| Local cassette p50 / p95 | 2.373 ms / 2.483 ms | 21 in-process happy-case runs, nearest-rank, one warm call first |
| judge-vs-human agreement | not measured yet | `python -m hemp review agreement --file labels/human_labels.template.csv`. Human labels stay empty |
| Live runs, 2026-10-17, xAI `grok-4.20-0309-non-reasoning`, `LIVE_LLM=1`, cap 0.15 USD | n=1: exit 0, checker accepted 1/1, pending, published 0, real 0.00785 USD, repo estimate 0.00879 USD. n=3: exit 0, checker accepted 1/3 (L2 `weak_grounding`+`repetition`, L3 `prerequisite_not_accepted`+`repetition`), 0 parse or format retries, real 0.03416 USD, repo estimate 0.03994 USD. live ejecutado en n=1 y n=3, muestra chica, sin tasa. Cost per approved piece is not quoted | `python -m hemp live --pieces 1` and `python -m hemp live --pieces 3`, outside CI |

CI on GitHub runs Python 3.11. The coverage number above is from Python 3.12.3 in this checkout. Re-run the command if you need the number on another interpreter. The 4-lesson course queue is not listed here as an agreement result.

## Not metrics of this repo

- Learner outcomes, completion, or satisfaction
- Reviewer throughput in a real week
- Production error rate
- A kappa from human raters. The CSV template is an import path only; this repo publishes no figure from it

## What to watch if this pattern is ever pointed at real drafts

- Share of drafts blocked, by finding code (`uncited_claim`, `redundancy`, `repetition`, others)
- Share of queue items still `pending` after the agreed review window
- Rubric version changes per month (a spike is drift of the instrument, not of the content)
- Any trace row whose provider is not `cassette` or `fake`
- Simulated or real cost versus the cap

Those watches are not implemented as a dashboard. The trace JSONL is the source a later dashboard would read.
