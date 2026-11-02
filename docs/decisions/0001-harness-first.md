# ADR 0001: Build a harness core with optional agent skills

- Date: 2026-11-02
- Status: Accepted design direction; implementation pending

## Context

Model iteration changes code, consumes compute, and makes decisions from experimental evidence. Conversation instructions can guide an agent, but they cannot independently own durable job state, enforce filesystem permissions, or guarantee that acceptance was computed under a fixed protocol.

Existing training programs also differ widely. Requiring a shared training loop would increase adoption costs and couple this project to model internals.

## Decision

Build a model-independent harness responsible for experiment contracts, candidate workspaces, task lifecycle, evidence, trusted evaluation, and promotion records.

Expose it through a CLI and a small API. Provide optional agent skills that call those interfaces. Keep training, model loading, and inference behind project adapters, with execution backends behind a separate interface.

Do not embed an autonomous research agent in the core. The core must also be usable by a human, a script, or CI without an LLM.

## Consequences

- State can survive agent conversation and controller restarts.
- Policies can be validated and enforced outside the proposing agent.
- Multiple agents can eventually use the same experiment protocol.
- Adapters must explicitly describe their artifact and inference interfaces.
- Strong protection requires a constrained execution environment; path checks alone are insufficient.
- A narrow first implementation is preferable to claiming support for arbitrary training repositories.

## Alternatives considered

### Skill-only

Useful for lightweight guidance and onboarding. It lacks an independent authority for state, evaluation, and promotion, so it will remain an optional client.

### A new training framework

Could offer tighter internal integration, but would require users to adapt training code. Existing training tools should remain usable through adapters.

### A complete autonomous scientist

Idea discovery, literature search, and paper writing are outside the initial model-iteration lifecycle and would substantially expand scope.
