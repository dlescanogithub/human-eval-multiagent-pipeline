# Runbook

There is no production deployment. "Operate" means run the commands in a checkout. Ownership below is for this private repo.

## Operate

```bash
python -m pip install -e ".[dev]"
python -m hemp demo --artifact-dir artifacts/demo
python -m hemp generate --artifact-dir artifacts/generate
python -m hemp review list --queue artifacts/generate/queue.json
python -m hemp review serve --queue artifacts/generate/queue.json --port 8765
```

`make demo` matches the first command if `make` exists. Artifacts are gitignored.

Logs are JSON lines on stderr. A happy demo logs `course_generated` and `synthetic_review_applied`.

## Monitor

- CI on the pull request: lint, mypy, pytest (coverage floor 80%), `python -m hemp eval`, the regression job (must exit 1 and contain `GATE_RED`), secret scan.
- Locally, `python -m hemp eval` prints one line per invariant.
- The drift file `fixtures/drift/simulated_weeks.json` is a planted dip in week W4. `python -m hemp drift` reprints the report. It is not wired to a live metric.

## Incidents

| Symptom | What to do |
| --- | --- |
| `eval` exits non-zero | Read the `FAIL` lines. Do not weaken the invariant to make it green. Fix the cassette or the checker, and say which. |
| `eval-regression` exits 0 | The gate failed to go red. CI treats that as a broken gate. Restore the block on repetition or missing citations. |
| `eval-regression` exits 2 (`GATE_BROKEN`) | A safety invariant failed or the expected finding code was absent. A bad lesson may have been marked approved, or the cassette no longer exercises the case. |
| Secret scan fails | Remove the secret from the tree and from history if it was pushed. Rotate the credential. Do not "allowlist" a real key. |
| Someone set `LIVE_LLM=1` in CI | Revert the workflow. CI must stay cassette-only. `hemp live` is not a CI step. |
| Live command exits 3, status `BUDGET_EXHAUSTED` | The spend or token cap was hit. Read the partial report under `var/live-evals/<stamp>/`. This is not a red gate. Do not loop the command. Raise `MAX_LIVE_SPEND_USD` or `MAX_LIVE_TOKENS` only if you intend to spend more. |
| Live provider times out or returns 5xx | The client retries 429, 5xx, and timeouts up to the attempt cap, then stops. Nothing is published. Wait and rerun one command, or stay on the cassette. |
| Live provider returns 401 or 403 | Not retried. Check the key outside the repo. Logs redact the key. Do not paste the key into a doc or a commit. |
| A draft looks like it followed an instruction inside a source document | Do not approve it. The checker should show `uncited_claim` if citations were dropped. `python -m hemp eval-regression` includes `regression_poison` and must still exit 1 with `GATE_RED`. |

## Rollback

Revert the commit. There is no database and no hosted service in this repo. The Docker image only runs `python -m hemp demo` as `nobody` and writes under `/tmp`.

If a local queue file was edited by mistake, delete `artifacts/` and run `generate` or `demo` again.

## Handoff

- Content questions (rubric, corpus, what "done" means): the person acting as content owner. In this portfolio that decision sits with Diego; the fictional role is the Nortia content owner.
- Gate, CI, cassettes, adapter flag: whoever is merging to this repo. CODEOWNERS is `@dlescanogithub`.
- Do not hand an agreement screenshot to a stakeholder without the sentence "synthetic raters, computation demo, not a human study."
- The README live table holds the two reviewed runs from 2026-10-17. Add another row only from a local report you reviewed. Do not turn n=1 and n=3 into a rate. Cost per approved piece is not quoted.
- judge-vs-human agreement: not measured yet. Do not fill `labels/human_labels.csv` with invented verdicts and then quote the kappa.
