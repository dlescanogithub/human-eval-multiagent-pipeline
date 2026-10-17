# Business case

Generic on purpose. A training organisation wants AI-assisted lessons, a quality check, and a record of what a human reviewed. The organisation in this repo is fictional: Nortia Learning. This is not a write-up of a real account.

## Problem

Drafts are cheap to generate and expensive to trust. The failure mode that matters here is a lesson that repeats an earlier lesson, or states a fact with no source, and still looks finished. A second failure mode is a clean draft that ships because nobody was assigned to sign it.

## What this repo actually shows

On the happy cassette, 4 lessons reach `approved` only after the checker is clean and the synthetic review count is met. One lesson (L2) needed a second writer pass because the first draft had an empty citation list. L4 asked for 3 raters because the critic's confidence was 0.55. The trace records the rubric version `1.0.0`.

The repeat cassette and the uncited cassette do not publish the bad lesson. Safety invariants still pass: the bad text is not marked approved, and the provider stays `cassette`.

## ROI model [EST]

Rates live in `fixtures/cost/illustrative_rates.json` and are labeled simulated. They are not a quote and not a public price list.

Measured inputs from `python -m hemp demo` on 2026-10-17, commit `ccafba8048f54f825c77af89744895f0c7f0c659`, package 0.1.3:

- 4100 tokens (2550 prompt + 1550 completion)
- 9 synthetic reviews
- 4 approved lessons

| | Assisted path | All-human baseline |
| --- | --- | --- |
| What is measured | tokens and review count | lesson count (4) |
| What is [EST] | 0.01 USD / 1k tokens, 8 minutes/review, 40 USD/hour | 120 minutes/lesson, 40 USD/hour |
| Simulated USD | 48.041 | 320 |
| Simulated USD per approved lesson | 12.01025 | 80 |

Difference: **271.959 simulated USD** on this 4-lesson course, about 85% lower **on these rates**. Change the rate card and the dollar gap changes. The direction of the gap is an assumption: that a cited draft plus a short review replaces a from-scratch write. This repo does not observe a real team, so it does not claim that saving.

Throughput, also [EST]: 8 minutes of review time per label. A 2-rater lesson is 16 minutes of review time in the model, against 120 minutes all-human. L4 is 24 minutes because it draws a third rater. That is the bottleneck the gate creates on purpose.

## Policy of what is published without review

**Nothing.** `allow` is not a flag in the publish rule. `generate` leaves every item `pending`. `demo` approves only after seeded labels, and those labels are marked `synthetic: true`. A piece with fewer labels than `required_raters` stays `pending`.

## What would change the case

If discovery says reviewers will not spend 8 minutes, the ROI flips toward the bottleneck described in [RISKS.md](RISKS.md). If the corpus is large or legally sensitive, the citation check in this repo is not enough; see [ADAPT_TO_A_REAL_CLIENT.md](ADAPT_TO_A_REAL_CLIENT.md).
