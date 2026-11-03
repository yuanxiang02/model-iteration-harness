# Three-stage project workflow

The agent-facing workflow is **assess decoupling -> review boundaries with the user -> iterate**. The CLI implements project registration, versioned review artifacts, exact-digest operator acknowledgment, and gates around the existing experiment runner. No model API or autonomous outer controller is required.

## 1. Assess and prepare decoupling

```bash
mih --state /outside/source/state project inspect /path/to/repository \
  --train train.py --eval eval.py
```

`--train` and `--eval` may be repeated. Entry paths can be relative to the source repository or explicit absolute paths. The command reads the supplied entrypoints, observes relevant Python function/import names with AST, records the baseline and dirty state, and writes `analysis.json` and `DECOUPLING.md`. It never edits source or launches training.

The assessment distinguishes:

| Finding | Meaning | Next step |
|---|---|---|
| `split-required` | The declared training and evaluation share an entrypoint | Separate trusted scoring and define checkpoint/inference or prediction export interfaces |
| `separate-entrypoints` | Declared entries exist and are different files | Review imports, reference access, checkpoint selection, and scoring semantics; independence is not proven |
| `uncertain` | Evaluation is undeclared or an entry is missing | Inspect the actual project and declare the missing boundaries; no automatic independence claim |

Filename/function observations cannot prove data flow, dynamic imports, or evaluator independence. A coding agent can use the plan to propose a refactor, but this prototype does not automatically rewrite an arbitrary training framework.

Keep the original model/training logic. Common adaptations are redirecting outputs, exposing checkpoint loading and inference, exporting predictions, and moving reference-dependent scoring behind a frozen entry. Development validation or best-checkpoint selection may legitimately remain inside training, provided their role and selection policy are explicit. Do not silently change metric semantics while separating code.

Preserve user edits and failed attempts. If source needs a refactor, review and commit that refactor before drafting the post-split baseline contract. The prototype requires the source repository to be clean at the specification and iteration boundaries.

To reassess an existing project, pass `--refresh`. The old assessment is archived, existing specification revisions remain on disk, and approval is invalidated. Refresh does not run training.

## 2. Generate a specification and review it with the user

Use a working v1 contract as described in [runtime.md](runtime.md):

```bash
mih --state /outside/source/state project draft project-ID /path/to/contract.json \
  --protect eval.py --protect metrics/ --protect data/ --max-experiments 3 --max-active 1
mih --state /outside/source/state project status project-ID
```

Each draft creates a new revision containing:

- `spec.json` (schema v2): resolved contract, baseline, protected paths/content, immutable input hashes, decoupling requirements and iteration policy.
- `BOUNDARIES.md`: the human-readable review document, including exact command, data/scorer references, scope, environment, seeds, budgets, and acceptance/promotion rules.

By default the policy permits one candidate, one active candidate and stops after
acceptance. The example proposes three total candidates with one active at a time.
Use `--continue-after-acceptance` only as part of an explicitly reviewed plan.
Failed/cancelled reservations count toward the total. Increasing/renewing limits
requires a new reviewed revision; historical approvals are not automatically
upgraded. See [control semantics](controllability.md).

Source `allowed_paths` declares editable paths. Optional `protected_paths` and repeated `--protect` declarations add explicit deny rules; deny wins even when an allowed directory contains protected files. Paths outside the allowlist are already disallowed. A scorer inside the repository is automatically added to the deny paths. A scorer that still shares a declared training entry is rejected.

For a required split, supply before/after exports from the same evaluation inputs:

```bash
mih --state /outside/source/state project compare-split project-ID \
  --before /path/to/original-predictions.jsonl \
  --after /path/to/separated-predictions.jsonl
```

The comparator requires unique nonempty IDs and exact structured equality, ignoring row/dictionary order. It does not silently tolerate numerical differences. All comparisons, including failures, are retained. Required split approval is blocked without a matching comparison bound to the current specification.

**Comparison limitation:** these are user-supplied exports. Their execution provenance, choice of inputs, and full training equivalence are not certified. A passing comparison alone is not sufficient evidence for a changed training/evaluation pipeline; the user must review the provenance and scope. A declared unknown assessment remains a human review responsibility.

After reading the exact specification with the user, an operator can record their explicit acknowledgment:

```bash
mih --state /outside/source/state project approve project-ID \
  --digest EXACT_SPEC_DIGEST --reviewer USER_OR_OPERATOR_NAME
```

The digest binds both structured specification and review Markdown. A stale digest is rejected. The agent must not execute this approval command on the user's behalf without explicit human acknowledgment of that specification. Test-suite approvals are simulated fixture attestations only.

**Authority limitation:** reviewer names are local operator metadata, not authenticated identities. The caller or an unrestricted same-user process can change the registry or use another state directory. This workflow enforces gates within a particular harness state; it does not independently authenticate a human or sandbox the calling agent. A separate approval authority/process would be needed for that stronger guarantee.

## 3. Agentic iteration under the approved specification

```bash
mih --state /outside/source/state iterate project-ID \
  --hypothesis "One declared model or training change" --factor "parameter: before -> after"
# The coding agent edits only the returned candidate workspace.
mih --state /outside/source/state submit exp-ID
# End the agent turn. The detached worker keeps running without model calls.
mih --state /outside/source/state status exp-ID
mih --state /outside/source/state report exp-ID
mih --state /outside/source/state promote exp-ID
```

`iterate --patch /path/to/change.patch` can apply a supplied patch. The experiment records the project/revision/digest. Submission enforces allowed/protected paths, the approved contract, and unchanged reference/scorer/input content. The worker rechecks the bound review during its normal evidence checks before advancing stages. A new draft or changed fixed content blocks further advancement; it does not retroactively erase previous results.

Every experiment declares its hypothesis and factors, and changes candidate source within the approved edit scope. Changing execution, evaluation, seeds, thresholds, data, scope or exploration limits requires a new specification and user review. The current prototype also binds a committed baseline; advancing that baseline requires a fresh draft/review. Baseline ratcheting under a persistent policy remains future work.

`project controls` reports remaining reservations, active candidates and stopping
reasons. `project pause --reason ...` blocks new creation, dispatch and promotion;
running jobs continue unless explicitly cancelled. `project resume --reason ...`
does not renew budget or approve a specification. Pause survives refresh and new
drafts; an agent must not resume an operator pause on its own.

The user controls whether an accepted development patch is applied through the separate explicit `promote --apply` action. Success does not automatically merge or push code.

## State and backwards compatibility

```text
projects/project-ID/
  analysis.json, DECOUPLING.md, state.json
  control.json, control-history/...
  history/assessment-ID/...
  revisions/revision-ID/
    spec.json, BOUNDARIES.md
    comparison-ID/{before.jsonl,after.jsonl,comparison.json}
    comparison.json, approval.json
    requests/..., iterations.json
```

The project stages are `assessed`, `awaiting_review`, and `approved`. Experiments retain their existing independent lifecycle.

For unregistered repositories, low-level `create` remains available for manual experiments and backwards compatibility. Once a repository is registered under a state root, `create`, `submit`, verification, and promotion cannot bypass its pending/drifted review in that same state root. An experiment created before registration cannot inherit approval retroactively; create a new experiment bound to the reviewed revision.

The core Codex skill now guides this controlled loop through JSON CLI calls.
Research/review addons are optional. There is no automatic refactoring engine,
external model API client or automatic agent wakeup. Legacy specifications without
an iteration policy remain readable; new candidates require a fresh bounded
draft/review. Existing runs retain their recorded semantics.
