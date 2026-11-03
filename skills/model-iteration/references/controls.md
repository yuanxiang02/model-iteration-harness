# Model iteration control contract

`mih` owns the experiment lifecycle; natural-language guidance alone cannot enforce
it. Each registered project has a reviewed specification revision. v0.3 adds an
`iteration_policy` to that specification, included in its review digest:

```json
{"max_experiments": 1, "max_active": 1, "stop_on_acceptance": true}
```

Propose limits while drafting, **before user acknowledgment**:

```text
mih --state STATE project draft PROJECT_ID CONTRACT --max-experiments 3 --max-active 1
mih --state STATE project controls PROJECT_ID
mih --state STATE iterate PROJECT_ID --hypothesis "..." --factor "steps: 100 -> 200"
```

The defaults propose one candidate and stop after the first acceptance. Add
`--continue-after-acceptance` to a draft only if continued exploration is part of
the reviewed plan. It does not authorize itself. A new revision renews its budget
only after acknowledgment and invalidates the previous revision for new actions.

`can_create` concerns a **new reservation**. Once the last slot is reserved it
becomes false, but submitting that already reserved candidate remains permitted
unless paused, stopped after acceptance or invalidated by protocol drift.

- Every candidate reserves a slot before materialization. Failed/cancelled
  candidates count; missing state after an interrupted creation remains a visible
  reservation. No automatic refund. Inspect/reconcile before further work.
- Prepared, running and unresolved/orphaned candidates occupy active slots.
  Active reservations from earlier revisions remain counted until reconciled;
  re-drafting does not make old work disappear.
  Reservations serialize under the project lock. This is an active-candidate
  limit, not a GPU scheduler or a global cross-project resource quota.
- Acceptance stops new candidates and new submission of already prepared ones
  when configured. Jobs already dispatched continue; promotion remains separate.
- `--factor` records claimed changed factors. The frozen proposal separately
  records actual changed paths and patch; it cannot prove semantic independence.

The execution contract also has `execution.total_timeout_seconds` (1–86400).
It covers baseline and candidate training, inference, scoring and acceptance in
one worker invocation. The default is the smaller of 3600 seconds and the sum of
per-command time limits for all planned commands. Child processes are polled;
trusted stages check at boundaries. Cleanup can take extra time. This is not a
strict aggregate CPU/GPU/memory/currency/token budget. Existing per-command limits
remain in force. An ETA is never treated as a successful exit.

Operator controls:

```text
mih --state STATE project pause PROJECT_ID --reason "Review budget before more runs"
mih --state STATE project controls PROJECT_ID
mih --state STATE cancel EXP_ID
mih --state STATE project resume PROJECT_ID --reason "Operator permits continuation"
```

Pause survives re-drafting/assessment refresh and blocks new candidate creation,
dispatch and promotion. It leaves running jobs alone. Resume neither approves
a specification nor renews budget. Follow explicit operator intent; an agent must
not resume a human pause on its own. Actions and reasons are retained in
`control-history/`. Operator identity is not authenticated by these local commands.

Historical specifications without a policy remain readable, and existing runs
retain their recorded semantics. Creating new candidates requires a new bounded
draft/review. Unregistered low-level manual experiments do not have project-level
controls; do not use them to bypass registered workflows. Same-user registry
tampering or switching state roots is outside this authority boundary.
