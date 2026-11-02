# MVP plan

The local prototype is implemented. The initial execution target was adjusted to macOS to validate real, low-resource examples on the development machine. Linux currently offers only explicitly selected `trusted-local` execution; an enforced Linux backend remains planned. Runtime usage and limitations are documented in runtime.md.

Implemented: independent worktrees, frozen evidence and scoring, detached local workers, job reconciliation, explicit cancellation/timeouts, development paired-bootstrap decisions, and explicit patch application. Automatic agent callbacks, confirmatory statistics, and remote execution remain planned. The scenarios below define behavioral checks, not production-security certification.

## Goal

Complete one auditable model-improvement cycle around an existing training program, without requiring a rewritten trainer or an LLM to watch the process.

## First vertical slice

1. Validate a proposed contract and resolve immutable source, environment, data, and evaluator references.
2. Save the contract and candidate patch; materialize a dedicated Git worktree.
3. Run existing Python/PyTorch training and inference commands through the local backend, with macOS subprocess restrictions and separate trusted scoring.
4. Persist state, reconnect after controller restart, and handle completion, failure, timeout, and cancellation.
5. Collect declared artifacts, run isolated inference, and calculate trusted scores.
6. Apply one documented paired comparison policy with an explicit development/confirmation boundary and declared confirmation trial budget. Missing required observations produce no successful acceptance.
7. Generate an experiment report and reviewable promotion artifact.
8. Apply that artifact only through an explicit promotion command against the expected baseline.

## Acceptance criteria

| Scenario | Required evidence |
|---|---|
| Two candidates execute | Code, outputs, and logs remain attributable to the correct experiment |
| A candidate tries to change evaluation | The configured boundary prevents the write; no forged score is accepted |
| Agent supplies a favorable stdout metric | Trusted scoring remains authoritative |
| Controller restarts during submission or training | It reconciles the original attempt and does not silently launch a duplicate job |
| Training crashes or exceeds its deadline | Failure and partial evidence are recorded; evaluation is not falsely reported as successful |
| An event is delivered twice | It does not duplicate evaluation or promotion |
| A required seed or prediction is missing | The declared failure policy applies; successful observations are not silently cherry-picked |
| A candidate clears the acceptance policy | A reviewable artifact is created; main code changes only on an explicit promotion action |
| The destination baseline changes | Promotion stops pending reconciliation and revalidation |
| A second model task is integrated | It uses a project adapter without changes to the core lifecycle |

## Reference integrations

Start with a small, public, reproducible classification task that can exercise the lifecycle inexpensively. Add a structurally different task, such as retrieval/ranking, to test the adapter boundary. Use public or synthetic data in repository examples; real private projects remain external integrations.

Do not launch expensive experiments merely to demonstrate the scaffold. Implementation tests should target behavioral guarantees with short-running jobs; model-benefit comparisons need a separate, budgeted evaluation plan.

## Later milestones

- One coding-agent integration after the CLI works without an LLM.
- DVC or a remote execution backend driven by a concrete user workflow.
- Additional acceptance policies for compression, non-inferiority, and resource tradeoffs.
- A compact experiment comparison view and broader model integrations.

## Out of the initial release

Built-in idea generation, literature search, paper writing, multi-agent orchestration, multi-cloud scheduling, a full tracking dashboard, and claims of universal model support or guaranteed improvement.
