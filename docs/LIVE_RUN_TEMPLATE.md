# Live run template

Paste a later row from `python -m hemp live-summary --dir var/live-evals/<stamp>` only after you have reviewed that local report. The two rows below are the reviewed runs from 2026-10-17. live was run at n=1 and n=3, a small sample, with no rate. Cost per approved piece is not quoted. judge-vs-human agreement: not measured yet.

| date | model | command | n | result | real cost (USD) | repo estimate (USD) |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-17 | xAI grok-4.20-0309-non-reasoning (writer, verifier, and critic) | `python -m hemp live --pieces 1` | 1 | exit 0. 7 calls: outline, draft L1, verifier, critic, revise, verifier, critic. Checker accepted 1/1. Item pending. Published 0. `live_result_claimed=false`. `LIVE_LLM=1`. `MAX_LIVE_SPEND_USD=0.15` | 0.00785 | 0.00879 |
| 2026-10-17 | xAI grok-4.20-0309-non-reasoning (writer, verifier, and critic) | `python -m hemp live --pieces 3` | 3 | exit 0. 25 calls. Checker accepted 1/3. L2 rejected for `weak_grounding` and `repetition`. L3 rejected for `prerequisite_not_accepted` and `repetition`. 0 parse errors and 0 format retries | 0.03416 | 0.03994 |

The repo estimate is higher because cached prompt tokens are priced as full input tokens. n=1 and n=3 do not support a rate.
