# Architecture proposal

This document describes intended behavior. None of the runtime guarantees below are implemented yet.

## Components

| Component | Responsibility | May depend on model internals? |
|---|---|---|
| Contract registry | Freeze baseline, edit scope, data/evaluator references, budgets, and acceptance policy | No |
| Workspace manager | Materialize a candidate and record its patch and ancestry | No |
| Execution backend | Submit, query, cancel, reconnect, and collect an external job | No |
| Project adapter | Describe training, artifacts, and candidate inference | Yes |
| Evaluation service | Validate prediction coverage and calculate scores under a fixed protocol | Scoring-specific, not an agent-editable training loop |
| Acceptance engine | Apply a versioned statistical/resource policy | Metric and sampling-unit specific |
| Promotion manager | Produce and explicitly apply an approved patch against an expected baseline | No |
| Agent client / skill | Propose a hypothesis, submit a patch, inspect evidence, request promotion | Optional |

The boundary is the experiment and its artifacts, not a universal tensor API or checkpoint format.

## Identity and evidence

Each experiment has an immutable ID, contract digest, baseline commit, parent experiment, candidate commit/patch digest, environment references, data references, seeds, budgets, and a comparison target. Resolved contracts must contain immutable references rather than branch names or mutable container tags.

Record the hypothesis and declared changed factors before launch. Independent directories do not establish controlled variables by themselves. A structural change may alter several factors; declare the scope instead of implying a one-factor result.

Persist the proposal and patch before training. Record artifacts with content hashes and locations. Keep failures and inconclusive evidence. Large-artifact retention can be configurable without removing the experiment's history.

Store trusted scores and acceptance records outside candidate-writable directories. An agent-provided result is a claim, not an authoritative measurement.

## Trust boundary

The proposing agent and candidate code are outside the trusted control plane. The controller, resolved contract, reference data, evaluator, acceptance policy, and promotion authority need a distinct writable boundary.

The first strong-isolation target is a Linux host with separate execution permissions or containers. Candidate processes receive only required training inputs and output mounts, without host control-plane access or a container-management socket. Read-only mounts alone are insufficient if the candidate retains another route to modify the host.

Inference that needs candidate architecture code executes in a restricted worker. That worker exports predictions keyed to expected example IDs. Trusted scoring checks identity, coverage, duplicates, and finite values before calculating the metric. It must not silently skip missing or invalid examples.

Hidden reference labels and acceptance decisions stay outside the candidate execution environment. Fixed data and evaluation hashes support provenance checks; hashes detect drift rather than prevent runtime tampering.

These are engineering controls with a declared threat model, not a claim of perfect security against arbitrary hostile code. A trusted/local development mode, if added, must clearly report its weaker boundary.

## Proposed lifecycle

```text
proposed -> materialized -> queued -> running -> trained -> evaluating
                                                        |
                                                     evaluated
                                                        |
                                                     accepting
                                                        |
                                  accepted / rejected / inconclusive

accepted -> promotion_requested -> promoted

execution paths may terminate as failed, cancelled, or timed_out
```

Lifecycle records and attempt records are distinct. Retrying execution or resuming an interrupted evaluation must not overwrite earlier attempts. Rejected and inconclusive candidates remain queryable.

Completion events must be idempotent. Evaluation starts only after checking the expected artifacts and training exit status. A recorded ETA triggers a status check, not a success transition. Cancellation, timeouts, and process-tree cleanup are backend responsibilities.

## Decoupled execution

The execution interface should support `submit`, `status`, `cancel`, and `collect`. Job IDs and enough backend metadata to reconnect are stored durably. Persist a submission intent before launch; use an experiment/attempt ID as an idempotency key or queryable external tag so recovery can reconcile a crash between submission and recording the job ID. Backends must report when this reconciliation cannot be guaranteed.

Ordinary code waits or polls. It invokes an agent only for an actionable review or failure. The agent receives a compact evidence summary and can request relevant logs.

On restart, reconcile external job state and evidence before launching another job. A missing process, missing output, or unparseable score must never be converted into a successful measurement.

The first backend will be local. DVC, SSH, Slurm, or other schedulers can implement the interface later; the core should not rebuild their scheduling machinery.

## Acceptance

Acceptance policies are frozen before candidate measurements are inspected. They declare metric direction, minimum effect or non-inferiority margin, resampling unit, required paired observations, confidence level, resource constraints, and failed-observation handling.

For a larger-is-better metric, one possible improvement policy requires the lower confidence bound of candidate-minus-baseline to exceed a declared minimum effect. This does not provide a universal statistical guarantee: assumptions, sample size, dependence, adaptive selection, and repeated comparisons still matter.

Training-seed comparisons and evaluation-sample resampling address different uncertainties. A single checkpoint's query bootstrap cannot certify robustness to training randomness. Small samples must be allowed to produce `inconclusive`.

The first implementation should support one documented comparison protocol. It must declare the boundary between development exploration and confirmation and record the confirmation trial budget. Additional policies should be added with justified assumptions rather than generic confidence labels.

## Promotion

Acceptance authorizes a reviewable promotion artifact. Applying it is a separate explicit command. Require that the destination baseline still matches the evaluated baseline. If the destination changes, the candidate needs reconciliation and revalidation.

Individually accepted patches cannot be assumed to retain their properties when combined. The combined candidate gets its own experiment and evaluation.

## Deferred choices

The implementation language is provisionally Python. A local transactional state store and content-addressed evidence metadata are candidate designs, not commitments to a particular database or artifact service. Schema validation, durability mechanics, backend protocols, and the first statistical method will be selected in the first implementation proposal.
