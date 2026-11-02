# Contributing

The project has a local prototype. Please distinguish working behavior from proposals in issues, documentation, and pull requests.

Useful early contributions include:

- A concrete model-training workflow that challenges the adapter boundary.
- A small implementation proposal for the MVP lifecycle.
- A reproducible failure case for state recovery, evaluation protection, or evidence attribution.
- A documented statistical policy with clear assumptions and selection limits.

Keep changes focused. Preserve failed-run evidence and user edits. Avoid expensive jobs, new infrastructure, or unrelated refactors without an agreed need.

When runtime code is added, validate behavioral guarantees with short-running examples. Record the commands actually run and their results. Do not present proposed behavior as tested behavior.

Repository examples must use public or synthetic data. Do not commit credentials, private datasets, model weights, experiment outputs, or organization-specific paths.

Install with `python -m pip install -e .`. Run `python -m unittest discover -s tests -v` in that environment. The core has no third-party runtime dependencies; optional training examples have separate requirements documented in docs/runtime.md. C-language training programs are outside the example scope.
