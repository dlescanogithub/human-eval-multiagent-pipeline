# How it works

Walkthrough for engineers and buyers. **100% synthetic; fictional domain.** The company is Nortia Learning and the course is "Foundations of Fictional Logistics". It is not a real client. The agreement numbers do not come from people.

The repository stays private until the checklist in [IP_AND_PROVENANCE.md](IP_AND_PROVENANCE.md) is done. That list is still open.

## The analogy

Think of an internal bulletin. There is a writer, a checker that may only assert what is on a source card, and an editor that sends the text back. Nobody sends the bulletin to press until the section lead has signed. The notebook of "we already said this" sits on the table: that is the running summary. If the writer tells the same paragraph again, the checker stops it, even when the paragraph sounds fine.

## The path, step by step

1. The course comes in as a file: objectives, nothing magical. The corpus is another small fictional card set, with ids (`F-WAYBILL`, `F-HUB`, and the rest).
2. The writer is a step replayed from a cassette. On the default path there is no model call.
3. For each lesson, the writer receives that lesson's outline entry and the summary of what was already accepted. The first version of lesson 2, on the happy cassette, states the hub fact with no citation. The checker sees it.
4. The verifier cassette gives an opinion. The checker does not trust it. It looks again at whether each claim has an id that exists and whether the text resembles that card (word Jaccard).
5. The critic cassette returns scores and a `request_revision` flag. If the checker is not clean, or the critic asks for another pass, and budget remains (maximum 3 on the happy course), the writer is called again. In the demo, lesson 2 is fixed on the second pass and then stops.
6. If the lesson is clean, its topics enter the summary. The next lesson sees them. If it is not clean, it does not enter: a cassette that repeats lesson 1 does not contaminate the summary, and the objective it should have covered stays uncovered.
7. What passed the checker goes to a queue. It is not published. Publishing is a local status, `approved`.
8. The demo fills the queue with synthetic labels, with a seed, and says so in the report. You can skip that: `python -m hemp generate` leaves the queue `pending`, and `python -m hemp review decide` or the page on `127.0.0.1` records a reviewer.
9. If critic confidence is under 0.7, the lesson asks for 3 reviewers instead of 2. On the happy course that happens to lesson 4 (confidence 0.55).
10. The publish rule reads rubric `1.0.0`: label count, safety at 5 on every label, and the mean of each dimension against its minimum. Only then does the status become `approved`.
11. Everything lands in a JSONL: each revision, the rubric version, who (or which cassette) acted, and the decision.

The eval gate does not compare the call list. It asks invariants: was anything published without a citation? Was anything marked blocking? Was there an external action? Does the summary match what was accepted? Does the simulated cost sit under the cap? Do the labels say they are synthetic?

## Glossary

| Word | What it means here |
| --- | --- |
| Cassette | A hand-written JSON with the response for each step. It is not a recording of a provider. |
| Running summary | The list of lessons, topics, and objectives already accepted. It is sent on the writer request and stored in the trace. |
| Claim | A sentence that asserts something, with source-card ids. |
| Checker | Code. It is not another model. |
| Rubric | `rubrics/rubric-v1.json`. Accuracy, clarity, flow, no-redundancy, safety. |
| Kappa / alpha | Agreement metrics. `python -m hemp agreement-demo` runs them on 48 synthetic items, with three documented reliabilities and a bootstrap interval. It is not a study with people. The 4-lesson course is not enough to cite an agreement figure. |
| Gate | `python -m hemp eval`. If the bad cassette does not fail quality, the regression command does not go red and CI flags it. |
| [EST] | An illustrative number, not measured on a real team. |
| MEASURED | A figure from a named command and date. The pytest line was re-measured on 2026-10-22. The cassette and live tables were measured on 2026-10-17 and were not re-run that day. |

## Limits, plainly

- It does not look at a vector database. The whole card set goes in. There are five facts.
- It does not publish outward. There is no LMS and no mail.
- It does not know whether something is true in the world. It knows whether the text resembles the card and whether you cited the id.
- The local page has no login. It is for your machine.
- The agreement the demo shows is a computation demo: synthetic raters, a seed, an interval. Do not cite it as people. If real labels show up later, the path is the CSV `fixtures/agreement/human_labels_template.csv` and `python -m hemp agreement-import`. This repo does not publish a human-agreement figure.
- The dollar cost comes from an invented rate card. The demo's tokens do come from the cassette.
- Judge-versus-human agreement is not measured. Until you fill in the sheet, the line is: judge-vs-human agreement: not measured yet.
- The repository is not cleared for the public. [IP_AND_PROVENANCE.md](IP_AND_PROVENANCE.md) is still the gate on that.

## Which part is actually multi-agent?

The repository name says multi-agent, and that can be read as more than the code does. In the default mode the writer, the verifier, and the critic do not call a model. They are responses stored in a cassette, in order. That is enough to test the orchestration, the checker, and the gates. CI runs only that mode. The fakes are deterministic: if you repeat the command, the gate gives the same result.

Live was run at n=1 and n=3, a small sample, with no rate. With `LIVE_LLM` set to 1, a cap `MAX_LIVE_SPEND_USD` greater than zero, and the URL, the key, and the model in the environment, the outline, the writer, the verifier, and the critic call an OpenAI-compatible chat API (completions over HTTP). Each step has a system prompt that names the step, the input, the JSON output schema with a minimal example, and that the reply must be only JSON. Each role can have its own model: `LLM_MODEL_WRITER`, `LLM_MODEL_VERIFIER`, `LLM_MODEL_CRITIC`. If those are unset, they use `LLM_MODEL`. Corpus text and what the previous role said travel as data, between `<untrusted-data>` marks, not as orders. The checker stays code: every cited claim, nothing uncited is published, and redundancy is measured the same way. The command is `python -m hemp live --pieces N`. `make live` is that command with `--pieces 1`.

Without that configuration the command exits 2 and does not open the network. If spend or tokens pass the cap, it exits 3 (`BUDGET_EXHAUSTED`). That is not a red gate: the red gate is still exit 1. JSON that does not match the step schema is rejected with an error that says what is missing, and there are at most two retries that carry that error as data. Each retry reserves the worst case against the cap before the call. Prices are not in the repo. If you want a dollar cost, export `LLM_PRICE_IN_PER_MTOK` and `LLM_PRICE_OUT_PER_MTOK`. That formula applies the input price to every prompt token, including cached ones when the provider reports them, so the number is an overestimate when there is a cache hit. The ledger records `cached_tokens` and does not give them a different price. If you do not have both prices, set `MAX_LIVE_TOKENS` and the cost stays `unknown`. On 2026-10-17 there were two independent runs, outside CI, with `LIVE_LLM` set to 1, cap `MAX_LIVE_SPEND_USD` at 0.15, and the model xAI `grok-4.20-0309-non-reasoning` on writer, verifier, and critic. `python -m hemp live --pieces 1` exited 0: 7 calls (outline, draft L1, verifier, critic, revise, verifier, critic), the checker accepted 1/1, the item stayed pending, nothing was published, and the live result was not claimed. Real cost 0.00785 USD; the repo estimated 0.00879 because it prices cached prompt tokens at the input rate. `python -m hemp live --pieces 3` exited 0: 25 calls, the checker accepted 1/3 (L2 rejected for `weak_grounding` and `repetition`; L3 for `prerequisite_not_accepted` and `repetition`), 0 parse errors and 0 format retries. Real cost 0.03416 USD; the repo estimated 0.03994, for the same reason. Those two runs are not enough for a rate. The table is in the README. judge-vs-human agreement: not measured yet.

An instruction embedded in a corpus document is not enough to publish or to drop the citation. There is a fake that obeys that instruction on purpose (`EMBEDDED-INSTRUCTION`). The gate still goes red and does not publish. That is in the forced regression.

The 48-item panel is still a computation demo of the formula. Agreement with a person is a different thing: `python -m hemp review export --n 30` writes `labels/human_labels.template.csv` with `human_verdict` empty. Until you fill it in by hand, judge-vs-human agreement: not measured yet.

A real organisation starts in [ADAPT_TO_A_REAL_CLIENT.md](ADAPT_TO_A_REAL_CLIENT.md): discovery, then shadow, then the gate. This repo is the rehearsal on fictional data. The dollars, the buyer, and what is measured versus not are in [BUSINESS_VALUE.md](BUSINESS_VALUE.md).
