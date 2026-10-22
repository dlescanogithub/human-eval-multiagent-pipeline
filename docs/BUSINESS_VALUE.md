# Business value

> **Important notice**
>
> - **Fictional buyer.** Nortia Learning, and the course "Foundations of Fictional Logistics", are invented for this exercise. They are not a client and not an employer. No real organisation's name, price, or volume is in this tree.
> - **Pending IP review.** This repository stays private until the checklist in [IP_AND_PROVENANCE.md](IP_AND_PROVENANCE.md) is done. The boxes are still open. This file does not clear that review.
> - Labels used below:
>   - **MEASURED**: a figure this repository recorded from a command, with the date.
>   - **[EST]**: a rate on `fixtures/cost/illustrative_rates.json` (`estimate: true`). Not a vendor price and not a quote.
>   - **[SYN]**: not used for any number in this file. No synthetic volume was added. Where a story would need a volume this repo does not have, the cell says the figure is absent.
>   - **SIMULATED**: the dollar total after measured counts are multiplied by the [EST] card, or the seeded drift and agreement panels. Not an invoice and not a human study.
>   - **UNVERIFIED**: not checked on 2026-10-22. Cassette, latency, agreement, and live rows below stay on their 2026-10-17 record.

Package 0.1.3. The pytest line was re-measured on 2026-10-22 against code revision `228dd93981cc1805d627d7b6f1248caa999618de`. Cassette, cost, latency, agreement, and live rows were recorded on 2026-10-17 at `ccafba8048f54f825c77af89744895f0c7f0c659` and were not re-run for this file. Sources: [../README.md](../README.md), [BUSINESS_CASE.md](BUSINESS_CASE.md), [COST.md](COST.md), [METRICS.md](METRICS.md), [SCOPE.md](SCOPE.md), [RISKS.md](RISKS.md).

## Buyer and problem

The buyer in this exercise is a training organisation that wants model-assisted lessons and a record of what a person reviewed. In the repo that organisation is Nortia Learning. The content owner owns the rubric and the publish decision. The person running the system owns the cassette or the optional live provider, the spend cap, and the rollback. That split is the business-strategy section of the README. It is not a named account.

The problem, from [BUSINESS_CASE.md](BUSINESS_CASE.md): drafts are cheap to generate and expensive to trust. A lesson can repeat an earlier lesson, or state a fact with no source, and still look finished. A clean draft can also ship because nobody was assigned to sign it.

What the lab does about that, on the fictional course only:

- A running summary of accepted lessons is passed into the next writer step.
- A deterministic checker, not the critic step, decides whether a draft is clean.
- Publication is a local status, `approved`, and only after rubric `1.0.0` has enough labels. `generate` leaves every item `pending`. Nothing is posted to an LMS, a site, or an inbox.
- Default writer, verifier, and critic steps are cassette playback. CI does not call a paid model.

## Value levers

Each lever is something the tree actually implements. The dollar reading of a lever is [EST] and is separated in the ROI section.

1. **Block a bad draft before a person reviews it.** On 2026-10-17 the repeat cassette and the uncited cassette did not publish the bad lesson. The poisoned-document cassette, a local fake that drops citations when the corpus contains `EMBEDDED-INSTRUCTION`, published 0. Safety invariants still passed. Source: README results table. UNVERIFIED on 2026-10-22 (not re-run).
2. **Keep later lessons from rebuilding a rejected topic in silence.** A lesson enters the running summary only when the checker accepts it. The repeat cassette therefore does not contaminate the summary. Source: [HOW_IT_WORKS.md](HOW_IT_WORKS.md) and ADR 0005.
3. **Require a signer count, and add a signer when the critic step is unsure.** Happy course: lessons 1–3 need 2 labels; lesson 4 needs 3 because critic confidence was 0.55 (threshold 0.7). Nine synthetic reviews in total. Source: README, measured 2026-10-17.
4. **Leave a trace a person can read.** Every trace row carries rubric version `1.0.0`, the revisions, and the publish decision. Source: README and `src/hemp/trace.py`.
5. **Keep a paid call behind an explicit cap.** `python -m hemp live` exits 2 unless `LIVE_LLM` is 1 and `MAX_LIVE_SPEND_USD` is greater than 0. Exit 3 (`BUDGET_EXHAUSTED`) when the cap is hit. The two recorded runs used a cap of 0.15 USD and stayed under it (real charges 0.00785 USD and 0.03416 USD). That is not a unit cost. Live was run at n=1 and n=3, a small sample, with no rate.

The direction of the dollar gap (a cited draft plus a short review replaces a from-scratch write) is an assumption already stated in [BUSINESS_CASE.md](BUSINESS_CASE.md). This repo does not observe a real team, so it does not claim that saving.

## Baseline versus target KPIs

"Target" here is the gate this repo already enforces on fixtures, or the [EST] card. It is not a promise to a buyer. Where the repo has no number, the target cell says so.

| KPI | Baseline | Target in this lab | How it is measured | Label |
| --- | --- | --- | --- | --- |
| Happy-gate invariants | No systematic check until the gate exists | 17/17 (`EVAL_PASS`: 10 safety, 7 quality) on the happy cassette | `python -m hemp eval` | MEASURED 2026-10-17. UNVERIFIED on 2026-10-22 |
| Forced regression | A bad cassette that still exits 0 would mean the gate is broken | Exit 1 and stdout contains `GATE_RED` | `python -m hemp eval-regression` | MEASURED 2026-10-17. UNVERIFIED on 2026-10-22 |
| Lessons approved on the happy course | All-human write of the same 4 lessons is the [EST] cost baseline, not a measured team | 4/4 after the checker is clean and the synthetic review count is met | `python -m hemp demo` | MEASURED 2026-10-17. UNVERIFIED on 2026-10-22 |
| Publish with no review | The failure mode in the problem statement | 0. `generate` leaves items `pending`. Fewer labels than `required_raters` stays `pending` | Queue status | MEASURED on the fixture path. Not observed in a team |
| Repeat or uncited lesson published | The failure mode in the problem statement | 0 on the repeat cassette and the uncited cassette | `python -m hemp eval-regression` | MEASURED 2026-10-17. UNVERIFIED on 2026-10-22 |
| Poisoned document published | A source card that contains an instruction | Published 0. Quality fail, safety pass | Forced regression | MEASURED 2026-10-17. UNVERIFIED on 2026-10-22 |
| Simulated USD for 4 lessons | 320 all-human | 48.041 assisted path, under an 80 cap | Measured tokens and review counts times the [EST] card | Counts MEASURED 2026-10-17. Dollars SIMULATED from [EST] rates |
| Minutes | 120 per lesson, all-human [EST] | 8 per label [EST]. Happy course uses 9 labels, 72 minutes | Rate card. Not a stopwatch on a person | [EST] |
| judge-vs-human agreement | not measured yet | No numeric target. The empty template must keep printing the not-measured line | `python -m hemp review agreement --file labels/human_labels.template.csv` | not measured yet |
| Live checker acceptance | No live evidence in CI | No rate target. Recorded results: n=1 accepted 1/1 and published 0; n=3 accepted 1/3 | `python -m hemp live`, outside CI | MEASURED as two runs on 2026-10-17. A rate is not supported |
| Unit tests and line coverage | Coverage floor 80% in `pyproject.toml` | Floor held | `python -m pytest --cov=hemp --cov-report=term-missing` | MEASURED 2026-10-22: 67 passed, 89.06%, Python 3.12.3, pytest 9.1.1 |

Learner outcomes, reviewer throughput in a real week, and a kappa from human raters are listed in [METRICS.md](METRICS.md) as not metrics of this repo. They are not given targets here.

## ROI model

One course of 4 lessons. No monthly volume is in the repo, so this is not a year-1 model and it has no payback in months.

**Formula.** ROI = (all-human simulated USD − assisted simulated USD) / assisted simulated USD. That is (benefit − cost) / cost if the benefit is valued at the all-human figure and the cost is the assisted path. Both dollar inputs depend on the [EST] card.

**[EST] assumptions, every one explicit.** From `fixtures/cost/illustrative_rates.json`, written for this repo on 2026-10-17, `estimate: true`. Not taken from a vendor price page.

| Assumption | Value | Label |
| --- | --- | --- |
| Model price | 0.01 simulated USD per 1k tokens | [EST] |
| Reviewer time | 8 minutes per label | [EST] |
| Reviewer rate | 40 simulated USD per hour | [EST] |
| All-human lesson | 120 minutes | [EST] |
| A cited draft plus a short review replaces a from-scratch write | Stated as an assumption in [BUSINESS_CASE.md](BUSINESS_CASE.md). Not observed | [EST] direction, not a measurement |
| Lessons in the course | 4 | MEASURED on the happy cassette, 2026-10-17 |
| Tokens | 2550 prompt + 1550 completion = 4100 | MEASURED from cassette `usage`, 2026-10-17 |
| Human reviews | 9 (2+2+2+3) | MEASURED, 2026-10-17 |

**Arithmetic on those inputs.** AI portion = 4100 / 1000 × 0.01 = 0.041 simulated USD. Human portion = 9 × 8 / 60 × 40 = 48 simulated USD. Assisted total = 48.041 simulated USD. All-human = 4 × 120 / 60 × 40 = 320 simulated USD. Gap = 320 − 48.041 = 271.959 simulated USD. ROI = 271.959 / 48.041. Per approved lesson on the assisted path = 48.041 / 4 = 12.01025 simulated USD. All-human per lesson = 80 simulated USD. The gap is 271.959 / 320 of the baseline (the README's "about 85% lower" on these rates).

Change the rate card and the dollar gap changes. If discovery says reviewers will not spend 8 minutes, the ROI flips toward the bottleneck in [RISKS.md](RISKS.md). That sentence is already in [BUSINESS_CASE.md](BUSINESS_CASE.md).

**What is not in the model.** No implementation hours, no licence fee, no monthly lesson volume, no fraud or legal-loss figure. Adding any of those would be a new number. This file does not add one. Payback in months is therefore not computed.

## Cost table

All dollar cells are **[EST]** or SIMULATED from the [EST] card, except the two live charges, which are the recorded invoices from those runs. Default cassette path: cost **zero** (no key, no network, no invoice).

| Scenario | Provider | Units | Cost | Latency | Quality | Source |
| --- | --- | --- | --- | --- | --- | --- |
| Happy course, demo and eval | `fake-cassette-v1` | 2550 prompt + 1550 completion tokens; 9 synthetic reviews; 72 human-minutes [EST] | 48.041 simulated USD (AI 0.041 + human 48). Cap 80. Per approved lesson 12.01025. All-human baseline 320 simulated USD | p50 2.373 ms / p95 2.483 ms, local, 21 runs, 2026-10-17. Not a vendor latency | 4/4 lessons approved; 17/17 invariants pass | [COST.md](COST.md). Tokens and review counts measured by `python -m hemp demo` on 2026-10-17. UNVERIFIED on 2026-10-22 |
| Repeat regression | same cassette style | AI on the calls in that cassette; 2 reviews on the clean lesson | 10.692467 simulated USD, under cap | not separately timed | quality gate red; bad lesson not published | `python -m hemp eval-regression` on 2026-10-17. [EST] card |
| Uncited regression | same | tokens only, no reviews (nothing queued) | 0.0182 simulated USD | not separately timed | quality gate red; nothing published | same date and card |
| Live, n=1, 2026-10-17, outside CI | xAI `grok-4.20-0309-non-reasoning`. `LIVE_LLM` 1. Cap 0.15 USD | 7 calls | real 0.00785 USD; repo estimate 0.00879 USD | not timed | checker accepted 1/1, item pending, published 0, live result not claimed | Recorded charges. No vendor price is stored in the repo |
| Live, n=3, 2026-10-17, outside CI | same model for writer, verifier, and critic | 25 calls. 0 parse errors and 0 format retries | real 0.03416 USD; repo estimate 0.03994 USD | not timed | checker accepted 1/3 (L2 `weak_grounding` and `repetition`; L3 `prerequisite_not_accepted` and `repetition`) | Recorded charges. The estimate prices cached prompt tokens as full input tokens |

Live was run at n=1 and n=3, a small sample, with no rate. Cost per approved piece is not quoted. judge-vs-human agreement: not measured yet.

When both price variables are set in the environment, and only then, the live formula is prompt tokens times `LLM_PRICE_IN_PER_MTOK` plus completion tokens times `LLM_PRICE_OUT_PER_MTOK`, per million. Cached prompt tokens are not discounted, so the formula overestimates a cache hit. Those prices are not stored in the repo. See [COST.md](COST.md).

## Measurement plan

Phase 0 is this repo. [SCOPE.md](SCOPE.md) records its exit as met on 2026-10-17: pytest, `python -m hemp eval` (`EVAL_PASS`), and `python -m hemp eval-regression` (exit 1, `GATE_RED`). Phase 1 (shadow on a real outline) and phase 2 (gate on for a real slice) are not started.

What to re-run when the tree changes, and what each command is allowed to support:

| Question | Command | Reading rule |
| --- | --- | --- |
| Did the checker and the queue tests hold? | `python -m pytest --cov=hemp --cov-report=term-missing` | Quote the date, Python version, passed count, and the total line coverage pytest-cov prints. Floor is 80%. The 2026-10-22 reading is in the README Proof section |
| Did the happy course stay inside the invariants? | `python -m hemp eval` | Exit 0 and `EVAL_PASS`. Do not treat one local run as a rate |
| Does a bad cassette still fail? | `python -m hemp eval-regression` | Must exit 1 and print `GATE_RED`. A pass here means the gate is broken |
| What did the cost card do to the measured counts? | `python -m hemp demo` | Report tokens and review counts as measured. Report dollars as SIMULATED from [EST] rates |
| Did the metric code run? | `python -m hemp agreement-demo` | Synthetic panel only. Not human agreement |
| Is there a human kappa? | `python -m hemp review agreement` on the empty template, or on a file filled outside the repo | Until `human_verdict` is filled by hand, the line is `judge-vs-human agreement: not measured yet` |
| What did one live process do? | `python -m hemp live` outside CI, then `python -m hemp live-summary` | One row per reviewed run. Do not compute a pass rate from n=1 and n=3 |

Watches listed in [METRICS.md](METRICS.md) for a later real corpus (share of drafts blocked by finding code, items still `pending`, rubric-version spikes, a non-cassette provider in the trace, cost versus the cap) are not implemented as a dashboard. The trace JSONL would be the source. They are not measured here.

A real rater study needs a protocol the owner writes and a filled CSV that is not committed if the labels are sensitive. This repo publishes no figure from that path.

## Risks

The ratings below are the ones already written in [RISKS.md](RISKS.md). They are not a new scoring. Owners are roles for the fictional exercise.

| Risk | As written in RISKS.md | What this repo does about it |
| --- | --- | --- |
| Incorrect content is published | Medium if the gate is skipped; low on the default path. Impact high | Checker blocks empty citations, weak overlap, and a small denylist. Publish requires reviews. The regression cassette must go red in CI |
| Reviewers become the bottleneck | High once a real queue exists; not observed here. Impact medium | The cost model shows human minutes. Not a staffing fix |
| Rubric drift | Medium over time; the fixture is static | Rubric version on every trace row. The drift report is a simulated series |
| Synthetic agreement is quoted as a human study | Medium, because a kappa still looks like a finding. Impact high | The panel is labeled a computation demo. ADR 0004. judge-vs-human agreement: not measured yet |
| A paid model is called from CI or from demo | Low. Impact medium | Demo and eval stay on the cassette. `hemp live` exits 2 without the flag and the cap. CI does not set the flag |
| A live run spends more than intended | Medium if someone enables `LIVE_LLM`. Impact medium | Worst-case reserve before each call. Exit 3 at the cap. The two recorded runs stayed under 0.15 USD |
| A source document carries an instruction the writer obeys | Medium once a real corpus is in play; exercised here by a fixture. Impact high if publication follows | Corpus text is delimited as data. `regression_poison` must stay red with nothing published |
| Live outputs change between runs | High when a real model is on. The two 2026-10-17 runs are not a repeat of the same command, so run-to-run change is not measured | Do not quote a pass rate. The cassette gate stays the CI evidence |
| The checker misses a paraphrase or blocks a legitimate revisit | Medium. Impact medium | Jaccard thresholds 0.55 and 0.82 are explicit. They are not tuned on real editors |
| Residual: a fluent uncited sentence that avoids glossary terms and the denylist | Stated as residual risk. The corpus is five cards | A human label is still required. "The model said so" is not a publish path |

Making the repository public before the checklist in [IP_AND_PROVENANCE.md](IP_AND_PROVENANCE.md) is done is out of bounds for this file. The checklist is still open.

## MEASURED versus not

**MEASURED**

- 2026-10-22, Python 3.12.3, pytest 9.1.1, package 0.1.3, code at `228dd93981cc1805d627d7b6f1248caa999618de`: **67 passed**, line coverage **89.06%**. Command `python -m pytest --cov=hemp --cov-report=term-missing --cov-report=json:coverage.json`. pytest-cov also printed that module hemp was previously imported and not measured. The percentage is the total it printed. Same passed count and same percentage as the 2026-10-17 line.
- 2026-10-17, commit `ccafba8048f54f825c77af89744895f0c7f0c659`: happy gate 17/17 and 4/4 lessons approved; regression exit 1 with `GATE_RED`; repeat, uncited, and poisoned cassettes published none of the bad lesson; writer calls and rater counts in the README table; agreement-demo coefficients on 48 synthetic items; local cassette p50 2.373 ms and p95 2.483 ms over 21 in-process calls; token counts 2550 and 1550; review count 9.
- 2026-10-17 live, outside CI, xAI `grok-4.20-0309-non-reasoning`: n=1 real 0.00785 USD (repo estimate 0.00879), checker 1/1, published 0; n=3 real 0.03416 USD (repo estimate 0.03994), checker 1/3, 0 parse or format retries. A small sample, with no rate.

**Not measured, and not filled in**

- judge-vs-human agreement: not measured yet.
- A pass rate, or a cost per approved piece, from the live runs.
- Any dollar saving in a real team. The 271.959 simulated USD gap is [EST] rates times measured counts.
- Reviewer minutes on a stopwatch. 8 and 120 are [EST].
- Learner outcomes, completion, or satisfaction.
- Run-to-run change of the live model. The two runs used different `--pieces` values.
- A prompt-injection result against a real model. The poison case is a local fake.
- Phase 1 shadow and phase 2 gate-on. [SCOPE.md](SCOPE.md) marks both not started.
- Clearance to make this repository public.
