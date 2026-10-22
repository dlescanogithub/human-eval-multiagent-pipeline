# Security

This repository is a private portfolio exercise. It ships no secrets and it does not want any.

## Reporting

If you found a problem in a private copy, tell Diego Lescano directly. There is no public bounty and no public disclosure process, because the repository is not public.

## What is in bounds

- The default provider is a cassette. `python -m hemp eval`, `python -m hemp demo`, and CI do not open a network connection to a model vendor.
- Configuration is environment variables only. `.env.example` has empty placeholders. The code does not load a `.env` file. Do not commit one.
- `python -m hemp.secretscan` runs in CI. It looks for private-key headers and the token shapes listed in the scanner. `docs/PROVENANCE.md` records the file's sha256. It is a tripwire, not a full secret-management program.
- The optional live provider raises `ConfigError` unless `LIVE_LLM=1` and the base URL, model, key, and a positive `MAX_LIVE_SPEND_USD` are set. `python -m hemp live` turns that into exit 2 and does not open a socket. A hit on the spend or token cap exits 3. Tests inject a fake transport and never take the network branch. Demo and eval ignore `LIVE_LLM`. The key is redacted in logs and exceptions. Prices are environment-only.
- The review page binds to `127.0.0.1` and has no authentication. Do not put it on a public interface. It writes the queue file you passed in. That is the whole effect.

## What you should not put here

- API keys, PATs, or customer data
- A real course, a real employee name, or a real company's materials
- A claim that the synthetic agreement demo is a human study, or a live-result number this repo did not measure

## Known limits

The checker looks for a small denylist ("publish without review", "ignore the reviewer", "skip the citation", "bypass approval") and for citations against the fictional corpus. It is not a safety classifier for arbitrary text. See [docs/RISKS.md](docs/RISKS.md) and the "What this does NOT prove" section in the README.
