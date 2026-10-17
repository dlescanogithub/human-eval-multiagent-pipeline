# 0004 — Synthetic labels are not a calibration study

## Status

Accepted. 2026-10-17. Updated the same day so the reported agreement figure is a 48-item computation demo, not the 4-lesson course queue.

## Context

Cohen's kappa, Fleiss' kappa, and Krippendorff's alpha need more than a handful of items before the arithmetic is worth showing. CI cannot hire raters. A 4-item course queue, even with a seeded clarity shift, does not support a statement about agreement. Inventing a human study would be worse.

## Decision

`agreement_demo.py` builds 48 items from seed `20261017`. Gold is `fail` when the index is divisible by 4, otherwise `pass` (12 fail, 36 pass). Three synthetic raters copy that gold label with design match rates 0.90 (`careful`), 0.75 (`moderate`), and 0.55 (`noisy`), and flip it otherwise. The report includes the realized match rate on that seed and a 95% percentile bootstrap over items (1000 resamples, seed `20261018`, sorted indexes 25 and 975). The disclaimer says the raters are synthetic and the numbers demonstrate the metric code.

The 4-lesson course still receives seeded labels so the publish rule can be tested. Those labels are not the agreement result.

`fixtures/agreement/human_labels_template.csv` is a header-only file (`item_id,rater_id,label`). `python -m hemp agreement-import` computes coefficients for a rectangular file the owner supplies later. The import disclaimer says the command does not certify the labels and does not publish a real-agreement figure. The empty template yields no coefficient.

## Consequences

The computation demo is reproducible and labeled. It is not evidence about people. A real study would be a new file, a protocol, and a different document. Until that file exists, this repository states no real agreement figure.
