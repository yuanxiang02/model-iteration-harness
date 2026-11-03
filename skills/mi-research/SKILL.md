---
name: mi-research
description: Investigate implementable approaches for improving an existing model, grounding candidate changes in the actual training code and cited papers or repositories. Use for model-iteration planning and targeted method surveys.
---

# Model approach research

Part of the Model Iteration Skills bundle. Read the shared
[packet protocol](../model-iteration/references/protocol.md). Use stage `research`;
the packet helper lives at `../model-iteration/scripts/packet.py`.

1. Anchor the goal in the actual model interface, bottleneck, metric, data splits,
   existing baseline and compute budget. Inspect only relevant project files.
   Separate measured bottlenecks from hypotheses. Missing information can become
   an explicit assumption or a targeted question; it must not become a fact.
2. Reuse relevant local notes and prior experiment results, then search available
   paper and repository sources for gaps. Record queries, dates and unavailable
   sources. Prefer primary papers and code; record repository commits when code
   matters. A repository README claim is not a reproduced result.
3. Write `research.md`: compare the closest practical approaches by mechanism,
   compatibility, expected failure modes, dependencies and approximate resource
   needs. Include a simple baseline. Avoid a large unrelated literature catalogue.
4. For each candidate, specify editable components, expected mechanism, changed
   factors, a cheap experiment that could refute it, and the evidence needed to
   justify further compute. Recommend a route with reasons, not an invented score.
5. Write `result.json` with payload `sources`, `candidates` and `recommendation`.
   Give sources stable IDs and connect candidate claims to those IDs. If search
   is unavailable, report the local evidence and limitations; do not invent
   citations or describe the survey as current or exhaustive.

This stage does not launch training, modify evaluation, approve project boundaries,
or establish novelty. Hand selected candidates to `mi-novelty` only when a novelty
claim matters; use `mi-review` for methodological review.

Adapted from ARIS research-lit, research-refine and experiment-plan. Retain the
bundle's [MIT notices](../model-iteration/references/attribution.md).
