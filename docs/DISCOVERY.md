# Discovery

Ten questions to ask before copying this pipeline into a real organisation. Each answer changes the design. None of these were asked of a real client; Nortia is fictional.

1. **Who is allowed to publish, by name and role?**
   If the answer is "the model," do not turn the gate on. This repo's publish rule requires labels. A single self-review (the personal study-guide case) would drop `base_reviews` to 1 and would be a different product.

2. **What must be true before a sentence can ship?**
   Here the rule is: every claim cites a corpus id and overlaps that card. If the real rule is "a lawyer signed the page," the checker is the wrong gate and the queue needs a role, not only a score.

3. **Where does truth live?**
   Five fictional cards are the whole corpus. A real handbook, a ticket system, or a changing policy site needs retrieval and a freshness rule. That is the design-only RAG line. Do not pretend the Jaccard check scales to it.

4. **What does a repeat cost?**
   The redundancy threshold is 0.55 Jaccard. A narrative course might want a lower bar (more blocking). A spiral curriculum that revisits a term on purpose might want a higher bar, or a per-topic allowlist. Ask before tuning.

5. **How wrong is a wrong fact?**
   Reputational and legal risk changes the review count and whether safety is a hard stop. This repo already refuses the denylist phrases and requires safety = 5 from every rater. A higher-stakes domain might require a named second role, which is not built.

6. **How long will a reviewer actually sit with one lesson?**
   The rate card assumes 8 minutes [EST]. If the answer is 30, the cost model and the adaptive rule (extra rater when confidence is low) need to be redrawn. The bottleneck risk in [RISKS.md](RISKS.md) gets worse, not better, if you add raters casually.

7. **What does the reviewer see?**
   Today: title, body, claims, citations, in a local page or a JSON file. If they need the source card side by side, or a diff against last quarter's lesson, the UI work is still design-only.

8. **Is there already a rubric, and who changes it?**
   Rubric `1.0.0` is in git. A content owner who changes weights every week will invalidate agreement trends. The drift report is a simulated series, not a detector you can point at production until the rubric version is stable enough to compare.

9. **What is the shadow period?**
   Recommended shape: run drafts and traces, publish nothing, compare checker findings with what reviewers would have blocked. Exit when the content owner trusts the block list. This repo can already stop at `generate` (nothing approved). It cannot ingest a real reviewer's historical decisions.

10. **What is out of bounds for the model vendor?**
    Default here is no vendor. The live command stays off unless `LIVE_MODE=1` and the base URL, model, key, spend cap, prices, and price date are all set. Turning that on is an explicit decision, not a default, and CI does not do it. The questions are region, retention, and whether lesson text may leave the machine.
