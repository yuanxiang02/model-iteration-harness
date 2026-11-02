# Local smoke validation

Recorded on macOS/arm64 on 2026-11-02. Exact seeds, upstream commits, observations, resource counters, and core source digests are in [local-smoke-2026-11-02.json](local-smoke-2026-11-02.json).

| Task | Baseline → candidate | Development decision | Total wall time | Peak child RSS |
|---|---|---|---|---|
| micrograd binary classification | Accuracy 0.6125 → 0.7250 | Inconclusive; improvement interval crosses zero | 2.85 s | 24.36 MiB |
| SimpleBayes text classification | Accuracy 0.5000 → 0.2500 | Rejected | 2.69 s | 48.34 MiB |
| CPU PyTorch character GRU | NLL 2.07394 → 1.73714 | Accepted under development policy | 41.84 s | 270.30 MiB |

Each result contains five fixed paired seeds. These examples test real training adapters, isolated candidates, independent scoring, and all three acceptance outcomes. They are tiny constructed fixtures, not confirmations of model generalization or reproductions of upstream performance. Repeated deterministic SimpleBayes runs do not provide additional independent statistical evidence.

The PyTorch example uses the pinned upstream `RNNModel`, 568 parameters, a single CPU thread, and separate training/checkpoint-inference processes. Importing PyTorch accounts for much of its overhead; model size is not an estimate of total process memory. No GPU or model API was used.

The accepted PyTorch candidate passed the explicit promotion readiness check. Its patch was not applied to the source example. Behavioral tests separately exercise actual patch application and refusal when the destination baseline changes.

The 16 core behavior checks passed on Python 3.9.6 and 3.14.5. They cover scope violations, frozen evaluator drift, runtime reference read/write denial on macOS, missing/duplicate predictions, invalid probabilities, source changes during execution, timeout, cancellation, detached reconnection, duplicate submission, queued launch recovery, orphaned children after worker loss, explicit promotion, and paired acceptance decisions. This is focused prototype validation, not a comprehensive security assessment.

Initial integration failures and their raw logs remain in ignored local evidence directories. The demonstrated fixes concerned interpreter compatibility and allowing `/dev/null` for PyTorch's imports; the fixed scorer and acceptance threshold were not relaxed.
