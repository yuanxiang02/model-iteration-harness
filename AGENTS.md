# Repository guidance

## Scope and status

This repository is a model-iteration harness, with optional agent skills as clients. It is currently a design scaffold. Do not claim working commands, completed protections, or benchmark results before implementing and verifying them.

Read README.md, docs/architecture.md, and docs/mvp.md before substantial changes. Keep existing model-training programs behind adapters rather than inventing a universal trainer.

## Implementation boundaries

- Keep experiment state and evidence durable outside candidate-writable directories.
- Treat proposals, training output, and candidate code as untrusted inputs to evaluation and acceptance.
- Do not weaken evaluation, data coverage, budgets, or acceptance policies to make a candidate pass.
- Document which checks are advisory and which are enforced, including their permission boundary.
- Preserve failed and inconclusive attempts. Never convert missing evidence into success.
- Reconcile recorded jobs before retrying. Do not silently duplicate training after a restart.
- Keep agent adapters thin; the core lifecycle must run without an LLM.

## Workflow

Prefer small changes that satisfy a documented MVP acceptance criterion. Use meaningful behavior checks for runtime changes; do not create tests that only mirror implementation details. Documentation-only edits do not require a new test suite.

Do not launch costly training runs or provision compute without user authorization. Do not publish secrets, private datasets, private model artifacts, or local organization-specific details.

No implementation setup or test commands exist yet. Add verified instructions when introducing runtime code.
