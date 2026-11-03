# Repository guidance

## Scope and status

This repository provides model-iteration skills backed by a local experiment runtime and JSON CLI. Read docs/skill-sources.md and the selected skills before changing their interfaces. Do not claim production isolation, universal model support, confirmation guarantees, or unverified benchmark results.

Read README.md, docs/architecture.md, and docs/mvp.md before substantial changes. Keep existing model-training programs behind adapters rather than inventing a universal trainer.

## Implementation boundaries

- Keep experiment state and evidence durable outside candidate-writable directories.
- Treat proposals, training output, and candidate code as untrusted inputs to evaluation and acceptance.
- Do not weaken evaluation, data coverage, budgets, or acceptance policies to make a candidate pass.
- Document which checks are advisory and which are enforced, including their permission boundary.
- Preserve failed and inconclusive attempts. Never convert missing evidence into success.
- Reconcile recorded jobs before retrying. Do not silently duplicate training after a restart.
- Keep agent adapters thin; the core lifecycle must run without an LLM.
- Keep unchanged upstream reference snapshots outside the installed skill bundle; preserve licenses, immutable URLs and content hashes. Use the versioned packet interface for research/review handoffs. Packet validity is not scientific acceptance or authenticated reviewer identity.
- Onboard existing model projects through assessment, reviewed boundaries, then iteration. Read docs/project-workflow.md and docs/agent-workflow.md.
- Never approve a project's boundary specification on the user's behalf without explicit acknowledgment of its exact content/digest. Implementation authorization is not project-policy approval; test approvals must be clearly simulated.
- Do not use another state root or the legacy create path to bypass an awaiting/drifted review.

## Workflow

Prefer small changes that satisfy a documented MVP acceptance criterion. Use meaningful behavior checks for runtime changes; do not create tests that only mirror implementation details. Documentation-only edits do not require a new test suite.

Do not launch costly training runs or provision compute without user authorization. Do not publish secrets, private datasets, private model artifacts, or local organization-specific details.

Runtime code uses the standard library. Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`, or install editable in a venv and run its Python. See docs/runtime.md for example requirements and sandbox boundaries. Model examples must use Python/PyTorch; C-language training programs are out of scope by user direction.
