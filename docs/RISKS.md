# Risks

Owners below are roles for the fictional exercise, not a staff list. "Content owner" would be a real person only after discovery.

| Risk | Probability | Impact | Mitigation in this repo | Owner |
| --- | --- | --- | --- | --- |
| Incorrect content is published and damages trust or creates a legal problem | Medium if the gate is skipped; low on the default path | High | Checker blocks empty citations, weak overlap, and a small denylist. Publish requires reviews. Regression cassette must go red in CI | Content owner for the rubric; operator for CI |
| Reviewers become the bottleneck and drafts pile up | High once a real queue exists; not observed here | Medium | Adaptive extra rater only when confidence is low. Cost model shows human minutes, so the pile-up is visible. Not a staffing fix | Content owner |
| Rubric drift: scores stop meaning the same thing | Medium over time; the fixture is static | Medium | Rubric version on every trace row. Drift report exists for a simulated series and is labeled simulated | Content owner |
| Synthetic agreement is quoted as a human study | Medium, because the numbers look tidy | High | Disclaimer on the agreement object. README says the clarity kappa is seeded. ADR 0004 | Whoever presents the repo |
| A paid model is called from CI or from a demo by accident | Low | Medium (cost and data leaving) | Default provider is the cassette. Adapter refuses to construct without `HEMP_ALLOW_NETWORK=1`. Tests block sockets | Operator |
| Secret committed | Low | High | `.env` gitignored, secret scan in CI, no keys in the tree | Operator |
| Local review page exposed | Low if it stays on localhost | Medium | Binds `127.0.0.1`, no auth, documented in SECURITY.md | Operator |
| Checker misses a paraphrase that is still a repeat, or blocks a legitimate revisit | Medium | Medium | Thresholds are explicit (Jaccard 0.55 / 0.82). They are not tuned on real editors | Content owner |
| Running summary hides a rejected lesson's topics and a later lesson rebuilds them badly | Low in the fixture | Medium | Rejected lessons are not added. The invariant checks the summary against accepted ids | Operator |

Residual risk: the corpus is five cards. A fluent uncited sentence that avoids glossary terms and the denylist can pass the checker. That is why a human label is still required, and why "the model said so" is not a publish path.
