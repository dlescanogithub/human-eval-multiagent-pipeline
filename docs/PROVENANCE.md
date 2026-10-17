# Provenance

## This repository

Original code and an original fictional corpus. Written for the private portfolio repo `human-eval-multiagent-pipeline`. Domain: Nortia Learning, course "Foundations of Fictional Logistics". No employer materials and no client materials were used.

## The eval-kit pattern

The brief asked for a documented copy of the eval kit in `dlescanogithub/agent-runtime-evals`, branch `cursor/agent-runtime-evals-mvp-7e58`, commit `55cfd4183fb2489d77fc9c8552e008274dc78f77`, where that was useful (`src/agent_runtime/evalkit/`, cassette provider, fake provider, JSONL trace, JSON logging, secret scan).

On 2026-10-17 the cloud agent that built this repo could not read that private repository. `gh` and the checkout token both received HTTP 404 / "repository not found". No blob was downloaded. Nothing in `src/hemp/` is a line-for-line copy.

What was implemented instead, under `src/hemp/`, as an original version of the same ideas:

| Idea | Where it lives here |
| --- | --- |
| Invariant evals, not golden tool-call traces | `src/hemp/evalkit/` |
| Cassette provider | `src/hemp/providers/cassette.py` |
| Fake provider for tests | `src/hemp/providers/fake.py` |
| JSONL trace | `src/hemp/trace.py` |
| JSON logging | `src/hemp/logging_setup.py` |
| Secret scan | `src/hemp/secretscan.py` |

If that reference repo becomes readable later, diff it against this package and record the comparison here. Until then, do not describe this code as a fork or a copy.
