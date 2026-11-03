# Skill extraction and adaptation / 来源与改造

Checked on 2026-11-03. This follows the earlier RSI harness survey, now inspecting
the selected projects' current fixed commits. It is a source review, not a local
reproduction of upstream workflows. Exact source URLs and hashes are in
[`third_party/sources.json`](../third_party/sources.json).

These adaptations are optional supporting material. The product's core is
[controllability during model iteration](controllability.md), implemented by the
main skill and local runtime. Neither research nor reviewer availability is
required for the controlled experiment lifecycle. Default installation is core
only; `--with-addons` includes the three supporting skills.

| Our entry | Upstream source documents | Kept | Changed |
|---|---|---|---|
| `mi-research` | ARIS research-lit, research-refine, experiment-plan | Grounding, problem anchor, implementable methods, minimal falsification experiments | Focus on an existing training repo; bounded available-source search; no required paper-writing workflow or hard-coded model |
| `mi-novelty` | ARIS novelty-check | Claim decomposition, closest work, mechanism-level comparison | Traceable search scope and categorical outcomes; no universal novelty score, fixed year window or required paid reviewer |
| `mi-review` | ARIS research-review, auto-review-loop, experiment-audit, result-to-claim; autoresearch reason | Separate reviewer contexts, trace retention, integrity checks, bounded rounds | Methodology/integrity roles; preserve dissent; no vote/LLM score as model acceptance; report unavailable reviewers honestly |
| `model-iteration` | autoresearch SKILL/plan/autoresearch/evals; existing local runtime | Explicit scope, measurable goal, bounded iteration and handoff | User-reviewed boundaries, isolated candidates, frozen scoring, durable failures, backend waiting, explicit promotion |

## Why the originals are not copied straight into discovery

ARIS is a broader research system, including paper writing, platform-specific
tool routing and shared helper contracts. Its selected current documents depend
on files beyond the snapshots. autoresearch includes generic software goals,
shipping and broader debate modes. Installing only these original files would
leave missing dependencies and inappropriate default behavior for model iteration.

Our four-entry bundle shares a versioned file interface. It uses host capabilities
instead of assuming Claude slash commands, Codex MCP, one model, one provider or
notification access. Search failure remains visible. Separate agents can use the
same model; we do not upgrade separate contexts to cross-family verification.

ARIS experiment-audit explicitly describes an advisory, never-blocking integration.
Our skill asks for investigation before positive claims on integrity failure.
This instruction and packet checks are not a security boundary and are **not yet
enforced as a new gate inside `mih promote`**. The runtime's own fixed evaluation
and acceptance checks remain authoritative. No automatic packet-to-runtime pipeline
or multi-agent transport is implemented by this first bundle.

## Interface and acceptance boundaries / 接口边界

- Skill stage: `request.json → result.json + evidence`. A checker validates fields,
  request linkage, evidence hashes and basic review completeness.
- Experiment stage: existing `mih` CLI. Boundary confirmation, execution, scoring
  and development acceptance retain their existing implementation.
- Human acknowledgment: required for the exact training-project specification;
  a skill result cannot act as an approval receipt.
- Research judgment: source coverage and reviewer judgment remain fallible. A
  valid JSON packet does not prove novelty or improvement.

The first bundle is ready for installation and workflow trials; independent
end-to-end agent behavior and cross-host compatibility are not yet validated.

## Attribution

All redistributed source documents are MIT-licensed and unchanged. Adapted
instructions preserve the relevant notices in the installed main skill at
[`references/attribution.md`](../skills/model-iteration/references/attribution.md).
Karpathy's program.md is reference-only, without copied source. Other previously
surveyed runners (ShinkaEvolve, OpenEvolve, Scholar Loop, DVC) remain architecture
references rather than sources of these three requested research/review skills.
