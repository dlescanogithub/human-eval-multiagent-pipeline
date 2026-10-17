# Provenance

## This repository

Original code and an original fictional corpus for the private portfolio repository `human-eval-multiagent-pipeline`. The domain is Nortia Learning and the course "Foundations of Fictional Logistics". Nothing in this tree comes from an employer or a client.

## Shared portfolio utilities

These small utilities are maintained in parallel across portfolio repositories and kept aligned. They are vendored copies, not a published library:

- cassette provider
- invariant checks
- JSON trace
- structured logging
- secretscan

`src/hemp/secretscan.py` is the copy in this repository. It is meant to stay identical to the copies in the other portfolio repositories.

src/hemp/secretscan.py sha256 854fb05c30f89011a18c6d85575fab5d37d259e51bf30a2c754105c608335aa8

Check that line with `make secretscan-hash`. `python -m pytest` checks the same digest.

## What was adapted here

The lesson pipeline, the fictional corpus, the rubric, the review queue, the agreement computation demo, and the optional live provider are specific to this repository. The shared utilities above were fitted to the `hemp` package: import paths, cassette step names, and the invariant list.

## Publication

Do not make this repository public until the checklist in [IP_AND_PROVENANCE.md](IP_AND_PROVENANCE.md) is done.
