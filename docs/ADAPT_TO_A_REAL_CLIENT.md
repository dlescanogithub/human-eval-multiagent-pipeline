# Adapt this to a real client

Short version: do not point this repo at a real corpus and call it done.

1. Run the discovery questions in [DISCOVERY.md](DISCOVERY.md). Write down who publishes, what must be cited, and what a wrong lesson costs.
2. Keep the repo's shape: spec, corpus the client is allowed to use, checker, queue, trace. Replace the Nortia fixtures. Do not reuse the fictional cards as if they were the client's.
3. Stay in shadow (`python -m hemp generate`, nothing approved) until the content owner has seen the blocks and agreed they are the right blocks.
4. Only then accept human labels (`synthetic: false`) and turn the publish rule on for a small set of lessons.
5. Replace the [EST] rate card with numbers the client actually uses, and label the date and the source. Until then, keep calling the dollars illustrative.
6. Leave retrieval, a hosted review UI, and a real agreement study out until they have an owner. The local page is not that UI. When labels exist, import them with `python -m hemp agreement-import` from a file shaped like `fixtures/agreement/human_labels_template.csv`. Do not quote the synthetic computation demo as the client's agreement.
7. Do not describe the work as a copy of a previous employer project. See [IP_AND_PROVENANCE.md](IP_AND_PROVENANCE.md).
