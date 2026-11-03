---
name: mi-review
description: Review model-iteration proposals or experiment evidence using independent methodology and integrity reviewers when authorized. Preserve reviewer traces, disagreements, and actionable findings without treating review as statistical acceptance.
---

# Model iteration review

Part of the Model Iteration Skills bundle. Read the shared
[packet protocol](../model-iteration/references/protocol.md). Use stage `review`;
the packet helper lives at `../model-iteration/scripts/packet.py`.

## Review contract

Review either a **proposal** or **results**, as specified in the request. Freeze
the input files/hashes, author identity if known, scope, and requested reviewer
count before dispatch. Default to two roles when multi-agent review is authorized:

- **Methodology:** does the mechanism address the stated bottleneck; are baselines,
  changed factors and minimal ablations adequate; what would falsify the claim?
- **Integrity:** are train/dev/test boundaries, evaluator, sample coverage, seed
  failures, resource budgets and reported results supported by actual artifacts?

Give each reviewer the same evidence packet, role-specific questions and an
isolated output directory. Ask for evidence locations, severity, proposed action
and a falsification check. Do not provide the author's desired verdict or another
reviewer's conclusions before the initial response. Reviewers inspect read-only
inputs and write only their own reports; host permissions determine enforcement.

## Execute and preserve

Use available host-native subagent tools only when delegation is authorized.
Inherit the user's configured model unless they request an override. Do not assume
tool names, a particular model, maximum reasoning settings, paid API access, or
permission to send private material to an external provider. Resolve capabilities
before dispatch. This bundle supplies instructions, not a reviewer API client.

Save each prompt, raw response, actual agent/session ID, requested/reported model
(or `unknown`), completion and scope. A different agent/session establishes a
separate context, not a different model family or statistical independence.
One agent acting out several roles is `self_review`, never multi-agent review.
If required independent reviewers are unavailable, record `unavailable`; a local
critique may still be delivered but cannot count as the requested completed review.

## Synthesize

Write `review.md` and payload `reviewers`, `findings`, `disagreements`,
`review_mode`. Preserve dissent and distinguish evidence-backed defects from
suggestions. Every reviewer record includes `id`, `role`, `status`, `agent_id`,
`model`, `prompt_path`, and `response_path`; paths point to hashed artifacts.
Statuses are `completed`, `unavailable`, or `failed`; unavailable records may use
null paths/agent IDs. Modes are `multi_agent`, `self_review`, or `unavailable`.

Use `changes_requested`, `ready_for_experiment`, `claims_limited`, or
`insufficient_evidence` as the decision. `ready_for_experiment` requires a completed
proposal review and no unresolved blocking finding; it grants no training budget,
boundary approval, promotion or statistical acceptance. Missing required reviewers
cannot yield a ready decision. Each finding has `id`, `severity` (`blocking`,
`major`, `minor`), `status` (`open`, `resolved`) and `evidence`.

Default to one review round. Further rounds must fit the requested budget and
address specific findings; stop at the declared round limit and retain unresolved
items. Failed integrity checks require investigation before positive result claims.
Review prose never overrides a failed/missing runtime acceptance result.

Adapted from ARIS research-review, auto-review-loop, experiment-audit and
result-to-claim, plus autoresearch's bounded iteration. Retain the bundle's
[MIT notices](../model-iteration/references/attribution.md).
