# Existing-training runtime handoff

Install the repository's Python package separately (`python -m pip install -e .`)
to get `mih`. Skill installation alone does not install the execution runtime.
No LLM API key is needed for this backend. Use absolute paths and keep `STATE`
outside the training repository. The runtime's current contracts and platform
boundaries are documented in the repository's `docs/runtime.md` and
`docs/project-workflow.md`; inspect `mih --help` and `mih project --help` as needed.

```text
mih --state STATE project inspect REPO --train train.py --eval eval.py
mih --state STATE project draft PROJECT_ID CONTRACT --protect metrics/
mih --state STATE project status PROJECT_ID
```

Static observations do not establish independent evaluation. If an entrypoint
needs splitting, prepare the refactor and compare relevant prediction exports
with `project compare-split`; that comparison is not proof of full training
equivalence. Draft and present the exact generated specification to the user.
After actual acknowledgment, record it using the returned digest:

```text
mih --state STATE project approve PROJECT_ID --digest DIGEST --reviewer REVIEWER
mih --state STATE iterate PROJECT_ID --hypothesis HYPOTHESIS
```

Apply the intended change in the returned candidate workspace within the approved
scope, then run `mih --state STATE submit EXP_ID`. Persist IDs and read `status`
or `report` on resumption. The backend performs ordinary
process waiting; this skill does not automatically wake the host agent.

```text
mih --state STATE status EXP_ID
mih --state STATE report EXP_ID
mih --state STATE recover EXP_ID
mih --state STATE promote EXP_ID
```

The first `promote` checks readiness. Applying a candidate is explicit:
`mih --state STATE promote EXP_ID --apply`. It writes an uncommitted patch to
the original model repository and does not commit, push or merge. Respect existing
user authorization and the evaluated baseline. Frozen protocol changes require a
new reviewed specification. The backend currently supports a development paired
bootstrap policy; do not relabel it as confirmatory evidence.
