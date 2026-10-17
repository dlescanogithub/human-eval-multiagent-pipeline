# 0004 — Synthetic labels are not a calibration study

## Status

Accepted. 2026-10-17.

## Context

Cohen's kappa, Fleiss' kappa, and Krippendorff's alpha are useful code to have, and they need more than one rater to run. CI cannot hire raters. Inventing a human study would be worse than showing the math on labeled synthetic data.

## Decision

`synthetic_raters.py` builds labels from the judge scores, the rubric, a seed, the lesson ordinal, and the rater index. The agreement report always carries `label: synthetic` and a disclaimer. The seeded clarity shift makes pairwise clarity kappa 0.5 on the happy course instead of a vacuous single score. Overall pass/fail kappa is 1.0 because every label stays inside the publish band; the report says so.

## Consequences

The numbers are reproducible (`rater_seed` 101 at commit `d8497e6`: clarity kappa 0.5). They are not evidence about people. A real study would be a new dataset, a protocol, and a different document.
