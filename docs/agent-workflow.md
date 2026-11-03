# Coding-agent operating guide

Use the existing shell/CLI integration. Keep the harness state outside the user's training source repository. Read [project-workflow.md](project-workflow.md) and [runtime.md](runtime.md) before onboarding.

The installable entry is now the `model-iteration` skill bundle; use `mi-research`,
`mi-novelty` and `mi-review` only for the stages the user needs. Their shared
[packet protocol](../skills/model-iteration/references/protocol.md) records inputs,
outputs and evidence. It does not replace the runtime or the review below.

1. Ask for or discover the actual training/evaluation entrypoints and existing environment from the user's project. Inspect only relevant files; preserve user edits.
2. Run `mih project inspect`. Treat AST observations as leads, not proof of separation. Explain the decoupling plan, including whether shared scoring needs to move, which interfaces must be exported, and what remains uncertain.
3. If a refactor is needed, prepare a reviewable change using the user's existing training code. Do not silently redefine metrics, data filtering, checkpoint selection, or validation behavior. Keep before/after exports and failure logs.
4. Draft the project specification. Present the allowed/protected paths, fixed evaluation/data, environment, budgets, seeds and acceptance rules to the human. Link the generated `BOUNDARIES.md` and show its exact review digest.
5. Stop at `awaiting_review` until the human explicitly acknowledges that specification. **Never manufacture a reviewer identity or approve your own plan.** Generic permission to implement this repository is not acknowledgment of a user's model-project specification. In tests, clearly mark simulated fixture approvals.
6. After acknowledgment is recorded, use `mih iterate` for one hypothesis and one attributable patch. Do not edit the original source or control-plane files to make a candidate pass.
7. Submit once, persist the returned experiment ID, and end the model turn while training runs. Ordinary code handles waiting; use compact `status` output when needed and `report` when results or actionable failures are ready.
8. Interpret accepted, rejected and inconclusive results honestly. Development acceptance is not confirmation. Failed/missing observations stay in the evidence.
9. If the contract needs changing, draft a new revision and return to human review. Do not widen scope, change the evaluator, lower a threshold, or switch state roots to bypass the existing gate.
10. Produce a reviewable promotion patch. Applying it to the original project is a separate explicit action; respect the user's authorization and baseline checks.

This guide is procedural instruction, not an OS authority boundary. The prototype constrains its candidate subprocesses and validates its registry; it does not automatically constrain an agent that already has unrestricted access to the host.
