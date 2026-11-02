# Local prototype guide

The core uses Python 3.9+ and the standard library. It runs on POSIX systems. The reference example driver should use Python 3.10+ because the pinned SimpleBayes source requires it. No Windows backend is implemented.

## Install and verify

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/mih --version
.venv/bin/python -m unittest discover -s tests -v
```

Without installation, `PYTHONPATH=src python3 -m mih --help` and `PYTHONPATH=src python3 -m unittest discover -s tests -v` work from this checkout.

## Real lightweight examples

```bash
.venv/bin/python examples/run_lightweight.py --task micrograd
.venv/bin/python examples/run_lightweight.py --task simplebayes
.venv/bin/python examples/run_lightweight.py --task torch-lm
```

Each example uses five fixed paired seeds and one declared candidate change. The first run downloads pinned source/license files into `.mih-demo/downloads`; SHA-256 checks apply to new and cached downloads. No upstream test suite, notebook, API server, or large dataset is launched.

| Example | Upstream | Training change | Dependencies |
|---|---|---|---|
| micrograd | karpathy/micrograd | 1 to 40 SGD steps | Standard library; vendored upstream scalar autograd |
| simplebayes | hickeroar/simplebayes | Unigrams to unigram + bigram features | Python 3.10+; a pinned small Snowball wheel is extracted locally, including its license |
| torch-lm | pytorch/examples word_language_model/model.py | 1 to 40 steps of an 8-hidden-unit GRU | An existing PyTorch installation; CPU only, one thread |

These are adapter-based smoke experiments on tiny constructed data, not reproductions of the upstream repositories' published results. Training budgets differ intentionally in the step-count examples; they test iteration mechanics, not equal-compute superiority.

The PyTorch adapter performs training and checkpoint inference in separate processes. It writes a real state-dict checkpoint and prediction distributions; trusted scoring computes held-out next-character NLL. The model has hundreds of parameters; framework import memory is substantially larger than model memory. The driver never downloads PyTorch.

The driver probes existing interpreters for PyTorch. To choose explicitly:

```bash
.venv/bin/python examples/run_lightweight.py --task torch-lm \
  --torch-python /absolute/path/to/python \
  --torch-python-path /absolute/path/to/site-packages
```

Declared package directories are recorded in the contract; ambient credentials and `PYTHONPATH` are not automatically inherited by candidate commands. The scorer runs with Python `-I` and does not use candidate import paths. System packages are not frozen into a container in this prototype, so dependency drift remains a reproducibility limitation.

Preparation runs outside the candidate sandbox. Candidate training/inference runs inside the selected mode. Existing example source edits are preserved and cause preparation to stop. Repeating a run creates another experiment and retains earlier failures; it does not overwrite their evidence. An example's accepted/rejected/inconclusive outcome is reported rather than tuned away.

Use `--prepare-only` to generate a source repository and working contract without starting training. `--root` selects a separate evidence directory. On Linux, add `--isolation trusted-local` for trusted code; `auto` fails rather than silently weakening restrictions.

## CLI lifecycle

Every command returns JSON. `--state` is a global option and goes before the subcommand. Keep it outside the training source repository.

```bash
mih --state /path/to/state create /path/to/contract.json
# Edit only allowed paths in the returned candidate workspace, or use create --patch.
mih --state /path/to/state submit exp-ID
# The detached worker continues after this command and the agent turn end.
mih --state /path/to/state status exp-ID
mih --state /path/to/state wait exp-ID --timeout 30
mih --state /path/to/state report exp-ID
mih --state /path/to/state recover exp-ID
mih --state /path/to/state cancel exp-ID
mih --state /path/to/state promote exp-ID
mih --state /path/to/state promote exp-ID --apply
```

`promote` without `--apply` only checks readiness. `--apply` requires an accepted development result, unchanged evidence and source, an unchanged destination baseline, and a clean destination. It leaves an uncommitted patch for review; it does not commit, push, or merge.

The current `report` is JSON. There is no GUI, MCP server, dedicated skill, built-in LLM client, automatic callback into an agent conversation, or remote scheduler. A coding agent can already use the CLI through its shell tool.

## Working contract v1

Prepare an example to obtain concrete paths. A minimal contract has this shape:

```json
{
  "schema_version": 1,
  "hypothesis": "One declared training change improves the fixed development metric.",
  "source": {
    "repository": "/absolute/training/repository",
    "baseline": "HEAD",
    "allowed_paths": ["train.py", "settings.json"]
  },
  "training": {
    "argv": ["{python}", "train.py", "{inputs}", "{output}", "{seed}"],
    "inputs": "/absolute/evaluation-inputs.jsonl"
  },
  "evaluation": {
    "reference": "/absolute/private-reference.jsonl",
    "metric": "accuracy",
    "direction": "maximize"
  },
  "execution": {
    "isolation": "auto",
    "timeout_seconds": 20
  },
  "acceptance": {
    "scope": "development",
    "seeds": [11, 22, 33, 44, 55],
    "confidence": 0.95,
    "minimum_effect": 0.0,
    "bootstrap_samples": 2000
  }
}
```

Paths resolve relative to the contract file. `HEAD` resolves to a full commit before execution. Reference labels must be outside the candidate source repository. Commands are argv arrays, with no implicit shell. Supported substitutions are `{python}`, `{seed}`, `{inputs}`, `{output}`, `{artifact}`, `{predictions}`, and `{workspace}`.

Optional `training.inference_argv` runs after training. Optional `training.python_paths` lists explicit existing package directories. Optional `evaluation.evaluator` selects a trusted standalone Python script, copied and hashed at creation. It must accept `--predictions`, `--reference`, `--metric`, and `--output`, and emit a finite `value` with the expected metric name. Custom evaluator correctness is the user's responsibility.

The default scorer supports `accuracy` and `nll`. Reference JSONL rows contain `id` and `target`; predictions contain `id` plus `prediction` or a normalized `probabilities` dictionary. Empty data, duplicate IDs, mismatched coverage, invalid probabilities, and non-finite scores fail the experiment.

Execution limits include a per-command wall timeout, a monitored log-size budget, a monitored total output budget, and per-process CPU/file-size limits. These are resource controls, not a strict aggregate memory limit. Peak child RSS is reported as a cumulative high-water mark, not summed memory across the run.

## Evidence and recovery

```text
state/
  runs/exp-ID/
    contract.json, integrity.json, sources.json, proposal.json
    candidate.patch, state.json, events.jsonl
    trusted/evaluator.py, trusted/reference.jsonl
    measurements.json, acceptance.json, *-train.log, *-score.log
  workspaces/exp-ID/{baseline,candidate}/
  outputs/exp-ID/{baseline,candidate}/SEED/
  inputs/exp-ID.jsonl
```

State updates use atomic replace with fsync and file locks. A lifetime worker lock prevents duplicate active workers. Reconnection observes persisted process identity; a queued launch intent can be recovered. If a worker dies while its recorded training process is alive, recovery marks `orphaned` and does not restart training. There is no automatic retry of interrupted experiments.

The host state directory is not an adversary-resistant evidence vault. The caller or another unrestricted process with the same user permissions can modify it. Automatic cleanup, arbitrary live-parent reattachment, full environment snapshots, and transactional promotion recovery after a host crash remain future work.

## Protection boundary

On macOS, `auto` selects `sandbox-exec`. Candidate subprocesses can write only their current worktree, output and scratch directories, plus `/dev/null`. They cannot read the configured reference, frozen scorer/control directory, or Git metadata, use the network, or send signals. Source snapshots detect runtime source edits; scopes reject disallowed edits before launch. Logs are captured in writable scratch and archived by the controller.

This constrains launched subprocesses. It does not automatically constrain an already-running Codex/other agent, hide every host file, or claim resistance to all hostile native code. `sandbox-exec` is platform-specific and deprecated; an enforced Linux/container backend remains unimplemented. `trusted-local` has no OS access boundary and is only for trusted code.

## Statistical boundary

Only exploratory development comparisons are implemented. Five or more complete paired seeds permit a deterministic percentile-bootstrap interval of the mean signed improvement. Missing pairs or fewer than five pairs are inconclusive; an interval above the declared effect is accepted, below it rejected, and overlapping it inconclusive.

Small-sample percentile intervals can be poorly calibrated. Repeating deterministic SimpleBayes runs does not create independent stochastic evidence. These intervals do not account for adaptive selection, evaluation-sample uncertainty, or repeated testing. Confirmation policies and independent holdout governance are planned; do not label a development acceptance a confirmed model improvement.
