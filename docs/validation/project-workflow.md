# Project workflow validation (v0.2.0)

The expanded local suite contains **32 behavior tests**: the original 16 experiment-runtime tests and 16 project-onboarding tests. They use small external Python jobs and no model API. All reviewer acknowledgments inside the test suite are explicitly simulated fixture attestations, not approvals of real user projects.

The project tests exercise:

- Read-only inspection, shared-entry detection, and explicit uncertainty without an evaluation declaration.
- Blocking iteration and legacy experiment creation before user review.
- Binding acknowledgment to both the exact specification and its review Markdown.
- A complete approved-project experiment through background training, trusted scoring, acceptance, and promotion readiness.
- Protected paths taking precedence over editable paths.
- Preventing a policy change from bypassing the specification through a low-level contract.
- Invalidation after fixed reference or review-document changes.
- Refusal to approve an edited contract whose reference paths disagree with the frozen-input metadata.
- New drafts and refreshed assessments not inheriting old approval; history remains available.
- Rejection of a scorer that still shares the declared training entry.
- Required split comparison, preservation of failed exports, acceptance of identical exports in a different row order, and rejection of changed comparison evidence.
- Preventing experiments created before registration from inheriting project approval retroactively.
- Machine-readable CLI output and structured errors for the pending-review stage.

The real lightweight PyTorch example was initially inspected and given a boundary draft without launching new model training. It remained `awaiting_review`, and an actual CLI `iterate` request was rejected before candidate creation. After the human explicitly acknowledged that exact specification, one project-bound round completed all 30 training/inference/scoring commands and passed development acceptance. Source, fixed inputs and review digests were rechecked; promotion readiness passed without applying the patch. See the [recorded round](reviewed-round-2026-11-02.json).

These checks validate the local state transitions and digest checks. They do not authenticate a human, prove arbitrary-program independence, certify full training equivalence from exported predictions, or constrain an unrestricted coding agent outside the subprocess sandbox. See [project-workflow.md](../project-workflow.md) for the authority and static-analysis limits.

The earlier [model smoke results](README.md) remain historical v0.1.0 evidence. They are not relabeled as new v0.2.0 model experiments.
