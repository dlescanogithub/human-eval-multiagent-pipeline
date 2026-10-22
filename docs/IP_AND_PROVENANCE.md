# IP and provenance

Keep this repository private. This file is a checklist for Diego before any publication. It is not a publication.

## What is in the repo

- Original Python for a multi-step lesson pipeline with a human review gate. Default roles are cassette steps.
- A synthetic corpus and synthetic cassettes about a fictional logistics course.
- Fictional organisation name: Nortia Learning.
- No employer name, no client name, no real course catalog, no real person's quotes, no real prices.

## Checklist before anyone makes the repo public

- [ ] Diego has read `docs/PROVENANCE.md` and agrees the shared utilities are the vendored portfolio copies described there, and that nothing in the tree comes from an employer or a client.
- [ ] Diego has searched the tree for employer names, client names, and old project names, and found none.
- [ ] Diego has confirmed the corpus text was written for this repo and is not lifted from a course, a handbook, or a ticket.
- [ ] Diego has confirmed no `.env`, key, token, or customer export is in history (`git log -p` and `python -m hemp.secretscan`).
- [ ] Diego has decided the license (MIT is in the tree) is the one he wants on a public repo.
- [ ] Diego has removed or rewritten anything he does not want a stranger to associate with him.
- [ ] Only after those boxes are checked does anyone change the GitHub visibility. This pull request does not do that.

## Explicit non-claims

This is not a replica of a real project. The agreement numbers are a computation demo on synthetic raters. This file does not state a real agreement figure. The dollar figures in the cassette cost card use an illustrative rate card marked [EST]. Two live runs are recorded in the README (2026-10-17, n=1 and n=3). live was run at n=1 and n=3, a small sample, with no rate. This file does not turn them into a pass rate or a human-agreement figure. The domain stays fictional: Nortia Learning, Foundations of Fictional Logistics.
