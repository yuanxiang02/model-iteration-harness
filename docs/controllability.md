# Controllability is the core product

The project standardizes **what an agent may change, how far it may explore,
which evidence counts and when a candidate may enter the original code**. Existing
trainers remain in place. Literature search, novelty and multi-agent critique are
optional aids, not required steps or the project's main contribution.

## Control surface

| Control | Enforced in the local runtime | Boundary |
|---|---|---|
| Scope | Approved allowed/protected paths; freeze baseline and patch | Path checks do not prove semantic single-factor changes |
| Evaluation | Fixed scoring/input/reference hashes, separate scorer, full prediction coverage | Custom scorer correctness remains the operator's responsibility |
| Exploration | Per-revision candidate reservations, active slots, stop-on-acceptance | Applies to registered projects in one state root |
| Execution | Per-command and whole-experiment wall limits; log/output caps; cancellation and recovery | No aggregate memory, GPU, token or monetary cap |
| Operator intent | Exact-digest specification acknowledgment; persistent pause/resume records | Local attestation, not authenticated identity |
| Evidence | Patch, declared factors, actual changed paths, logs, failures, scores and acceptance | Same-user writable state is not an adversarial evidence vault |
| Promotion | Explicit operation after acceptance and evaluated-baseline checks | No automatic commit/push/merge; development result is not confirmation |

## Reviewed exploration limits

`project draft` now generates specification schema v2; the experiment contract is
still v1. The policy is covered by the specification's exact review digest:

```bash
mih --state STATE project draft PROJECT_ID contract.json \
  --max-experiments 3 --max-active 1 --protect metrics/
```

The default is one candidate, one active candidate and stop after acceptance.
`--continue-after-acceptance` proposes a different stopping policy; it requires
the same exact user review. Candidates reserve before materialization under the
project lock. Invalid patches, failures and cancellations consume slots. Reserved
work interrupted before state creation remains visible and occupies an active
slot; no silent retry or refund is performed. A new reviewed revision may provide
a renewed budget. Re-drafting alone cannot authorize it.

```bash
mih --state STATE project controls PROJECT_ID
mih --state STATE iterate PROJECT_ID \
  --hypothesis "More optimization steps reduce development NLL" \
  --factor "steps: 100 -> 200"
```

`controls` reports policy, used/remaining reservations, active experiment IDs,
pause state and reasons why a new candidate is blocked. `--factor` is required
before spending a registered project's slot. Actual changed paths/patch are
recorded independently, and the declaration is frozen. The CLI cannot verify that
the claimed mechanism is correct or that two changes are causally independent.

The active limit includes prepared candidates and unresolved orphaned work,
not only running processes. Active reservations from prior revisions remain
visible and occupy slots until finished or cancelled; a new draft cannot hide
them. After acceptance, no new candidate or prepared-job
dispatch is permitted when stop-on-acceptance is enabled. Already dispatched jobs
may finish. Promotion of the accepted candidate remains possible unless paused.

## Waiting, time limits and interruption

Set `execution.total_timeout_seconds` in the existing contract for a whole-worker
budget across baseline/candidate seeds and training/inference/scoring/acceptance.
The default is `min(3600, planned_command_count * timeout_seconds)`, with a valid
range of 1–86400 seconds. Child-process polling and trusted-stage boundary checks
enforce it; termination/cleanup can extend elapsed time slightly. This is not a
hard kernel deadline for every controller instruction. No LLM is needed to wait.

```bash
mih --state STATE project pause PROJECT_ID --reason "Operator requests review"
mih --state STATE cancel EXP_ID
mih --state STATE project resume PROJECT_ID --reason "Operator permits continuation"
```

Pause blocks new creation, dispatch and promotion. It is intentionally a drain
operation; it does not cancel existing training. Use explicit per-experiment
cancel to stop a job. A pause survives re-drafting and assessment refresh. Resume
does not renew budget or approve a specification. Skills must not resume an
operator pause on their own. Both actions retain reasons in `control-history/`.

## Compatibility and authority

Historical runs/contracts retain their recorded per-command and review semantics.
Specifications without an exploration policy remain readable; new candidates
require re-drafting and explicit review. No historical approval is automatically
upgraded. Low-level manual runs on unregistered projects remain available, without
project-level exploration gates. Registered `create`/`iterate`/`submit`/promotion
paths use the same controls, so changing CLI entrypoints does not renew a budget.

These controls apply within the configured state root. They do not stop a host
agent with unrestricted same-user permissions from modifying the registry or
bypassing this system entirely. macOS child-process restrictions and explicitly
trusted local execution remain as described in [runtime.md](runtime.md). No new
authenticated authority, universal sandbox or statistical confirmation is claimed.

The research packet interface is supplementary: valid packets, claimed novelty
and positive reviews cannot grant budget or replace runtime acceptance. Optional
addons are installed with `scripts/install_skills.py --with-addons`; the default
installation includes only `model-iteration`.
