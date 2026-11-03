---
name: model-iteration
description: Coordinate auditable iteration of an existing model-training project, from targeted research and reviewed edit boundaries to isolated experiments and evidence review. Use for improving an existing training pipeline through coding agents.
---

# Model iteration

Keep the user's existing trainer. Use the host agent for reasoning and the `mih`
runtime for experiment execution. This skill does not supply an LLM API client,
an automatic agent wakeup service, or a security boundary around the host agent.

## Interface

Read [the packet protocol](references/protocol.md) when starting or resuming a
stage. Natural-language requests are valid: normalize them into `request.json`
before work. Store packets outside the training repository, in a new stage
directory. Never overwrite an earlier run. The helper is
`scripts/packet.py`, resolved relative to this installed skill directory.

## Route only the work needed

- **Explore approaches:** use the bundled `mi-research` skill. Produce grounded
  candidate changes and cheap falsification experiments.
- **Assess a novelty claim:** use `mi-novelty`. Ordinary engineering improvements
  do not require a novelty check. A negative novelty result does not make an
  engineering improvement useless.
- **Review a proposal or results:** use `mi-review`. It supports independent
  reviewers when delegation is authorized and available; report reduced coverage.
- **Execute a candidate:** follow [the runtime handoff](references/runtime.md).

Read the selected skill's `SKILL.md` from its sibling bundle directory; do not
assume a slash command or tool exists for invoking it. All four skills are
installed together. Research and review can run without `mih` or a model API key.

## Execution boundaries

1. Inspect relevant training/evaluation code and the existing environment. Prepare
   a concrete separation plan if scoring shares candidate-editable logic. Do not
   silently change sample filtering, metrics, checkpoint selection, or data splits.
2. Use `mih project inspect` and `project draft` to produce a versioned boundary
   specification. Present the generated `BOUNDARIES.md` and exact digest, including
   allowed/protected paths, evaluation/data, seeds, environment, and budgets.
   Await the user's acknowledgment of that specific specification. Record existing
   acknowledgment once; implementation permission is not specification approval.
3. Create one candidate with `mih iterate`. Record the hypothesis, changed factors,
   baseline and patch. Apply the change only in the returned candidate workspace,
   before submission. Separate folders do not establish controlled variables.
4. Submit once. Save project/experiment IDs before ending the model turn. Ordinary
   code handles waiting. Read compact status or the final report on resumption;
   reconcile a recorded job before retrying. ETA is a check time, not completion.
5. Review the trusted report and underlying evidence. Preserve failed, rejected and
   inconclusive attempts. Development acceptance is not independent confirmation.
6. Produce a reviewable promotion patch. `promote --apply` is a separate action,
   governed by the user's authorization and the evaluated baseline. Never change
   a gate, evaluator, state root or reference data to make a candidate pass.

Do not bypass pending/drifted project approval through low-level runtime commands.
Instructions constrain cooperative behavior; actual process restrictions depend
on the configured execution backend and do not constrain an unrestricted host agent.

## Deliverables

Complete the packet with `python scripts/packet.py check RUN_DIR` after writing
`result.json` and its evidence files. For the iteration stage, link the runtime's
actual report, not a score copied from training stdout. Do not label a packet check
as experiment acceptance: it validates structure, file hashes and request linkage.

Adaptation sources and MIT notices are in [references/attribution.md](references/attribution.md).
