# Model Iteration Harness

A harness for reproducible, evaluation-controlled model improvement with coding agents.

[中文说明](README.zh-CN.md) · [Architecture](docs/architecture.md) · [MVP](docs/mvp.md) · [Design decision](docs/decisions/0001-harness-first.md)

> **Status: design stage.** This repository contains the initial design and proposed experiment contract. There is no executable harness, published package, or implemented isolation guarantee yet.

## The problem

An agent can edit training code and launch experiments. Turning those edits into a reliable model improvement requires more:

- Evaluation code, data splits, and acceptance rules must stay under trusted control.
- Each candidate needs an isolated workspace, an explicit baseline, and a durable evidence record.
- Training should run independently of the agent conversation. Completion or failure should trigger evaluation and review.
- Promotion needs a declared acceptance policy, rather than whichever score an agent happens to report.

## What we are building

Model Iteration Harness will manage the lifecycle around existing training programs:

```text
Frozen experiment contract + baseline
                  |
             Agent proposal
                  |
         Isolated candidate workspace
                  |
         Submit training and persist job ID
                  |
        Completion / failure event
                  |
      Trusted evaluation and acceptance
                  |
      Reviewable patch and promotion record
```

The harness will own experiment identity, workspace lifecycle, job state, evidence, evaluation policy, and promotion. Agents will propose changes and interpret results through a small CLI/API surface. Agent skills will be optional integration layers.

Training frameworks remain project-specific. An adapter will connect an existing command or scheduler to the harness; users should not need to rewrite their model as a framework-specific `Trainer` class.

## Planned experiment contract

The [proposed example](examples/experiment.proposed.json) describes:

- An immutable baseline and a candidate's parent.
- Allowed edit paths and externally controlled evaluation references.
- Training and inference commands, declared outputs, seeds, and resource budgets.
- An acceptance policy with explicit uncertainty and failure handling.
- A completion event that can trigger evaluation and an optional agent review.

The example is a design proposal, **not a supported configuration or runnable quickstart**. Its revision marker will change as the first adapter is implemented.

## Design commitments

1. **Persist evidence for every attempt.** Failed or inconclusive experiments are part of the archive. Promotion is a separate decision.
2. **Keep the evaluator authoritative.** Training stdout cannot certify model quality. Frozen scoring consumes outputs through a declared interface.
3. **Separate reproducibility from access control.** A Git worktree isolates files for organization; enforced permissions or sandboxing provide protection from runtime writes.
4. **Wait in ordinary code.** Job polling, deadlines, and retries do not need an LLM call. ETA is a fallback check, not proof of completion.
5. **Declare what acceptance means.** Improvement, non-inferiority, and resource constraints need different policies. Statistical conclusions must match the sampling unit and account for repeated selection.
6. **Make recovery explicit.** Restarting the controller must reconnect to a recorded job before it considers launching another one.

## Initial scope

The first vertical slice will target a Git repository and a local training process on Linux, with separate training/inference and scoring permissions. It will produce a reviewable promotion artifact; changing the user's main branch will remain an explicit action.

Remote execution, DVC/Slurm integration, additional agents, and richer statistics can follow once the lifecycle works across two different model tasks. See the [MVP plan](docs/mvp.md) for acceptance criteria and limits.

## Relationship to existing tools

This project draws on established ideas in [autoresearch](https://github.com/karpathy/autoresearch), [DVC Experiments](https://dvc.org/doc/user-guide/experiment-management), [ShinkaEvolve](https://github.com/SakanaAI/ShinkaEvolve), and other agent experiment systems. Its focus is a reusable boundary between coding agents, existing training programs, trusted evaluation, and evidence-based promotion.

We intend to integrate execution and tracking tools where practical. Framework comparisons and reliability claims will require reproducible experiments.

## Contributing

At this stage, useful contributions are concrete training workflows, critiques of the contract, and small implementation proposals tied to the MVP. Please see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE).
