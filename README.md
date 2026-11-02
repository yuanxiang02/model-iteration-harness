# Model Iteration Harness

A harness for reproducible, evaluation-controlled model improvement with coding agents.

[中文说明](README.zh-CN.md) · [Run the prototype](docs/runtime.md) · [Architecture](docs/architecture.md) · [MVP](docs/mvp.md)

[Recorded local validation](docs/validation/README.md): three real training adapters exercise accepted, rejected, and inconclusive development outcomes.

> **Status: local prototype, v0.1.0.** The CLI runs real baseline/candidate experiments, records evidence, scores predictions, and explicitly applies accepted patches. macOS child-process restrictions are implemented and tested; Linux uses an explicitly selected `trusted-local` mode. This is not a production sandbox or a statistical confirmation system.

## Quickstart

The core has no third-party runtime dependencies and supports Python 3.9+. Use Python 3.10+ for all examples; the PyTorch example can reuse a separate existing interpreter.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/mih --help
.venv/bin/python -m unittest discover -s tests -v

# A few seconds of pure-Python neural-network training; no GPU or model API.
.venv/bin/python examples/run_lightweight.py --task micrograd

# CPU-only text training and separate inference using an existing PyTorch install.
.venv/bin/python examples/run_lightweight.py --task torch-lm
```

The preparation script downloads source/license files pinned by commit and SHA-256. It never installs PyTorch or starts an API server. On Linux, explicitly add `--isolation trusted-local` when running trusted examples. See [runtime instructions](docs/runtime.md) for the CLI, environment selection, evidence, and limitations.

## The problem

An agent can edit training code and launch experiments. Turning those edits into a reliable model improvement requires more:

- Evaluation code, data splits, and acceptance rules must stay under trusted control.
- Each candidate needs an isolated workspace, an explicit baseline, and a durable evidence record.
- Training should run independently of the agent conversation. Completion or failure should trigger evaluation and review.
- Promotion needs a declared acceptance policy, rather than whichever score an agent happens to report.

## What the prototype does

Model Iteration Harness manages the lifecycle around existing training programs:

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

The harness owns experiment identity, workspaces, job state, evidence, evaluation policy, and explicit promotion. Agents can call the JSON CLI. No built-in agent loop or model API key is required.

Training frameworks remain project-specific. Adapters connect existing training/inference commands to the harness; users do not need a framework-specific `Trainer` class. Remote scheduler adapters are still planned.

## Experiment contract

The working v1 contract is documented in [runtime.md](docs/runtime.md). It describes:

- A resolved baseline commit and a declared hypothesis.
- Allowed edit paths and externally controlled evaluation references.
- Training and inference commands, declared outputs, seeds, and resource budgets.
- An exploratory acceptance policy with explicit uncertainty and missing-seed handling.
- Durable state that can be queried from a different agent session or process.

The older [proposal-0 example](examples/experiment.proposed.json) is retained as design history and is not accepted by the CLI. Automatic agent callbacks, experiment ancestry, and confirmatory repeated-testing policies are not implemented.

## Design commitments

1. **Persist evidence for every attempt.** Failed or inconclusive experiments are part of the archive. Promotion is a separate decision.
2. **Keep the evaluator authoritative.** Training stdout cannot certify model quality. Frozen scoring consumes outputs through a declared interface.
3. **Separate reproducibility from access control.** A Git worktree isolates files for organization; enforced permissions or sandboxing provide protection from runtime writes.
4. **Wait in ordinary code.** Job polling, deadlines, and retries do not need an LLM call. ETA is a fallback check, not proof of completion.
5. **Declare what acceptance means.** Improvement, non-inferiority, and resource constraints need different policies. Statistical conclusions must match the sampling unit and account for repeated selection.
6. **Make recovery explicit.** Restarting the controller must reconnect to a recorded job before it considers launching another one.

## Current scope

The first vertical slice targets Git repositories and detached local workers on POSIX. On macOS, candidate subprocesses cannot write outside their workspace/output/scratch roots, read the configured protected reference/control paths, access the network, or signal other processes. The calling coding agent is not automatically sandboxed by this library.

Pure-Python micrograd training, SimpleBayes text classification, and a tiny CPU PyTorch language model are the reference integrations. PyTorch training and inference are separate processes with trusted scoring afterward. See the [MVP plan](docs/mvp.md) for implemented behavior and remaining work.

## Relationship to existing tools

This project draws on established ideas in [autoresearch](https://github.com/karpathy/autoresearch), [DVC Experiments](https://dvc.org/doc/user-guide/experiment-management), [ShinkaEvolve](https://github.com/SakanaAI/ShinkaEvolve), and other agent experiment systems. Its focus is a reusable boundary between coding agents, existing training programs, trusted evaluation, and evidence-based promotion.

We intend to integrate execution and tracking tools where practical. Framework comparisons and reliability claims will require reproducible experiments.

## Contributing

At this stage, useful contributions are concrete training workflows, critiques of the contract, and small implementation proposals tied to the MVP. Please see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE).
