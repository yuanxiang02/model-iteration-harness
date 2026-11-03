# Stage packet interface v1

All bundle stages use the same file interface. The skill reads a request, performs
the selected work with host tools, and writes a result plus evidence. The helper
does not call an LLM, search the web, dispatch reviewers or submit training.

Create a stage directory **outside the training repository**:

```bash
python /path/to/model-iteration/scripts/packet.py init /path/to/run/research-01 \
  --stage research --repository /path/to/model-repo --goal "Reduce development NLL"
```

The command refuses an existing directory. It records the actual current Git
commit and whether tracked/untracked changes are present; a dirty tree is not
rejected for read-only research, but cannot be claimed as a frozen experiment
baseline. Runtime iteration still requires its own clean-source checks.

Request fields (all required):

```json
{
  "interface_version": "1",
  "run_id": "run-unique-id",
  "stage": "research",
  "goal": "Reduce development NLL",
  "project": {"repository": "/absolute/model-repo", "baseline_commit": "git-sha", "dirty": false},
  "constraints": {},
  "inputs": []
}
```

Stages: `research`, `novelty`, `review`, `iteration`. Set constraints before work:
search/time budgets, reviewer count/rounds, delegation authorization, and compute
limits where relevant. These are agent inputs, **not runtime-enforced budgets or
an approval receipt**. Review requests include `review_kind` (`proposal`/`results`)
and `required_reviewers` (positive integer) in constraints. Input references are
objects with `path` and `sha256`; paths are absolute local files. The checker
verifies they still match. Use earlier checked `result.json` and relevant artifacts
as inputs to the next stage. Do not make up past results.

Finish `result.json` in the same directory:

```json
{
  "interface_version": "1",
  "run_id": "run-unique-id",
  "stage": "research",
  "request_sha256": "sha256-of-request-file-bytes",
  "status": "completed",
  "decision": "candidate_options",
  "summary": "Two implementable approaches were identified.",
  "artifacts": [{"path": "research.md", "sha256": "sha256-of-file-bytes"}],
  "limitations": [],
  "next_actions": ["Review the selected proposal"],
  "payload": {"sources": [], "candidates": [], "recommendation": "..."}
}
```

Status is `completed`, `needs_input`, `unavailable`, or `failed`. Non-completed
results use decision `insufficient_evidence` and describe missing capabilities or
information. Every result includes at least one hashed evidence/report artifact;
report files stay inside the stage directory. Reject path escapes and mismatched
hashes. Keep packets in an operator-controlled location; same-user writable hashes
are drift checks, not authenticated provenance or protection against a hostile host.

| Stage | Completed decisions | Required payload |
|---|---|---|
| research | candidate_options / insufficient_evidence | sources, candidates, recommendation |
| novelty | overlap_found / distinct_candidate / insufficient_evidence | claims, closest_sources, search_scope |
| review | changes_requested / ready_for_experiment / claims_limited / insufficient_evidence | reviewers, findings, disagreements, review_mode |
| iteration | submitted / awaiting_boundary_review / accepted_development / rejected / inconclusive / failed | project_id, experiment_id, runtime_report |

Use `null` for an unavailable iteration ID/report; never invent one. `runtime_report`
is the relative path of a hashed report copied into this directory when available.
Other large artifacts remain managed by the runtime. An iteration result is a
handoff envelope, not a substitute for runtime acceptance or promotion authority.

`python .../scripts/packet.py check RUN_DIR` verifies required types, stage-specific
fields, request linkage, referenced file hashes and basic review completeness. It
does not establish citation truth, reviewer identity, novelty, model improvement,
OS isolation or human approval. Agents fill semantic payloads; check success is
not a positive scientific judgment. Consumers must still inspect the evidence.

Use `python .../scripts/packet.py hash FILE` to obtain a file's SHA-256. Request
hashes refer to the exact JSON file bytes, not a reserialized object. After work
starts, do not edit the request to fit a result; create a revised stage directory.

To resume, check the existing packet and runtime job IDs first. Preserve completed
packets; create a new directory for a revised request or review round. No automatic
discovery/advancement of a multi-stage pipeline is implemented in this first bundle.
