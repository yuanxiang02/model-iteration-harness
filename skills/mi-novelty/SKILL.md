---
name: mi-novelty
description: Check specific model-method novelty claims against traceable prior work, documenting overlap, implementation differences and search limitations. Use before asserting a research contribution, not as a gate for every engineering improvement.
---

# Model novelty check

Part of the Model Iteration Skills bundle. Read the shared
[packet protocol](../model-iteration/references/protocol.md). Use stage `novelty`;
the packet helper lives at `../model-iteration/scripts/packet.py`.

1. Extract falsifiable claims: problem, mechanism, training signal, architecture,
   evaluation setting and claimed difference from the baseline. Separate a new
   mechanism, an application, an empirical finding and an integration contribution.
2. Search available primary literature and implementations using mechanism terms,
   aliases and adjacent methods. Cover relevant foundational work and recent work
   through the actual search date; do not hard-code conference years. Save the
   query log, sources inspected and coverage gaps in `novelty.md`.
3. For each claim, identify the closest prior work and compare concrete operations,
   objective, information access, assumptions and evaluation protocol. Inspect
   relevant method text/code before asserting a material difference. Title-only
   and abstract-only comparisons must be labeled as limited evidence.
4. Classify each claim as `overlap_found`, `distinct_candidate`, or
   `insufficient_evidence`. A distinct candidate means a specific difference is
   supported within the searched scope; it is not proof that no prior work exists.
   Explain whether the difference could matter and what experiment could test it.
5. Write `result.json` with payload `claims`, `closest_sources`, `search_scope`.
   If retrieval is unavailable or a claimed difference cannot be checked, return
   `insufficient_evidence`. Do not substitute an LLM opinion or a 0–10 novelty
   score for source evidence.

Independent review is optional and must be authorized and available. If used,
preserve its real identity and response. Same-family reviewers are not evidence
of cross-family verification. Do not disguise a self-review as another agent.

Keep useful engineering candidates even when they are established techniques;
correct their positioning. This stage does not approve boundaries or training.

Adapted from ARIS novelty-check. Retain the bundle's
[MIT notices](../model-iteration/references/attribution.md).
