# Metrics

Success, for this repo, means the gate can go green on a clean course and red on a bad one, with a trace a person can read. It does not mean a business outcome was observed.

## Measured (2026-10-17, package 0.1.0, commit `d8497e6`)

| Metric | Value | Command |
| --- | --- | --- |
| Tests | 21 passed | `python -m pytest` (pytest 9.1.1, Python 3.12.3) |
| Line coverage | 89.99% | same command, floor 80% in `pyproject.toml` |
| Happy gate | `EVAL_PASS`, 16/16 invariants | `python -m hemp eval` |
| Regression gate | exit 1, `GATE_RED` | `python -m hemp eval-regression` |
| Happy lessons approved | 4/4 | `python -m hemp demo` |
| Revision used | L2 writer_calls = 2 | same |
| Adaptive raters | L4 required_raters = 3; others 2 | same |
| Clarity Cohen kappa (synthetic) | 0.5 | same, seed 101 |
| Overall Cohen kappa (synthetic) | 1.0 | same; single category, pass |
| Local cassette p50 / p95 | 2.404 ms / 2.65 ms | 21 in-process happy-case runs, nearest-rank |

CI on GitHub runs Python 3.11. The coverage number above is from Python 3.12.3 on the agent that built the repo. Re-run the command if you need the number on another interpreter.

## Not metrics of this repo

- Learner outcomes, completion, or satisfaction
- Reviewer throughput in a real week
- Production error rate
- A kappa from human raters

## What to watch if this pattern is ever pointed at real drafts

- Share of drafts blocked, by finding code (`uncited_claim`, `redundancy`, `repetition`, others)
- Share of queue items still `pending` after the agreed review window
- Rubric version changes per month (a spike is drift of the instrument, not of the content)
- Any trace row whose provider is not `cassette` or `fake`
- Simulated or real cost versus the cap

Those watches are not implemented as a dashboard. The trace JSONL is the source a later dashboard would read.
