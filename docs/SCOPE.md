# Scope

No fees. No staffing plan. Phases are a way to talk about what is in the tree and what is not.

## Assumptions

- The domain stays fictional until a separate engagement brings a real corpus under a real owner's name.
- Reviewers will accept a structured rubric with five dimensions. That is an assumption, not a finding.
- "Published" means a local status. There is no downstream system.
- The cassette is a stand-in for a model. It is deterministic so the gate can be tested offline.
- Dollar rates in the cost card are illustrative [EST].

## Phase 0 — this repo (implemented)

- Course spec, synthetic corpus, happy cassette, two regression cassettes.
- Running summary, revision loop, deterministic checker, invariant eval, forced red gate.
- Queue on disk, CLI, local page, synthetic labels, agreement computation demo (48 synthetic items), CSV import template, simulated drift, JSONL trace.
- Optional live provider, off by default, exit 2 without `LIVE_LLM=1` and the spend cap, exit 3 when the cap is exhausted. No live result is claimed. Cost per approved piece: not measured yet.
- CI: lint, types, tests with an 80% coverage floor, eval, regression-must-fail, secret scan.

Exit criteria for phase 0, met on 2026-10-17 at commit `52541f8d6ec255e2a3aafaaf8d3db9267a283f70`, package 0.1.2: `python -m pytest` (59 passed, 89.07% coverage), `python -m hemp eval` (`EVAL_PASS`, 17/17), `python -m hemp eval-regression` (exit 1, `GATE_RED`).

## Phase 1 — shadow on a real outline (not started)

- Replace fixtures with a corpus the content owner is allowed to use.
- Keep publish disabled (`generate` only) for an agreed set of lessons.
- Compare checker findings with the owner's own notes. Do not quote synthetic kappa as if it were theirs.

Exit: the owner can point at ten blocked drafts and say the block was right, in writing. Not done here.

## Phase 2 — gate on (not started)

- Turn the publish rule on for a small slice.
- Human labels only (`synthetic: false`), from people with the role discovery named.
- Cost cap reviewed against a real rate, not the [EST] card.

Exit: a week of traces where every approved piece has the required human labels and no uncited claim. Not done here.

## Out of scope

- Vector search or a hosted retrieval service
- Adapters for a managed model platform
- A multi-tenant review product
- A calibration study with paid or volunteer raters
- Sending email, posting to an LMS, or opening a pull request in a docs site
- Any fee, quote, or staffing number

## Rollback of this phase

Phase 0 rolls back by reverting the git commit. There is no production deploy. See [RUNBOOK.md](RUNBOOK.md).
