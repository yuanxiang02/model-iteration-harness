"""Inspect -> review a boundary specification -> permit agent experiments.

Approvals are explicit operator attestations tied to exact document digests.
They are not an authentication system against an unrestricted same-user agent.
"""

import ast
import copy
import hashlib
from pathlib import Path
import re
import uuid

from .storage import HarnessError, canonical, digest, load, locked, now, save


def project_id(repository):
    return "project-" + hashlib.sha256(str(Path(repository).resolve()).encode()).hexdigest()[:16]


def directory(store, identifier):
    if not re.fullmatch(r"project-[0-9a-f]{16}", identifier):
        raise HarnessError("Invalid project ID")
    path = store.root / "projects" / identifier
    if not (path / "state.json").is_file():
        raise HarnessError("Unknown project: " + identifier)
    return path


def state(store, identifier):
    path = directory(store, identifier)
    result = load(path / "state.json")
    result["directory"] = str(path)
    if result.get("revision"):
        revision = path / "revisions" / result["revision"]
        result.update(specification=str(revision / "spec.json"), boundaries=str(revision / "BOUNDARIES.md"))
        result["spec_digest"] = review_digest(revision)
    return result


def _entry(repository, entry):
    value = Path(entry)
    return value.resolve() if value.is_absolute() else (repository / value).resolve()


def _inspect_file(path):
    record = {"path": str(path), "exists": path.is_file(), "functions": [], "imports": []}
    if not path.is_file():
        record["note"] = "Entry point missing; no code executed"
        return record
    if path.stat().st_size > 512 * 1024:
        record["note"] = "Static inspection skipped: file exceeds 512 KiB"
        return record
    record["sha256"] = digest(path)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeError) as error:
        record["note"] = "Static parse unavailable: " + type(error).__name__
        return record
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if re.search(r"train|eval|validat|metric|score|accuracy|recall|ndcg|perplex", node.name, re.I):
                record["functions"].append({"name": node.name, "line": node.lineno})
        elif isinstance(node, ast.Import):
            record["imports"].extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            record["imports"].append(node.module)
    record["imports"] = sorted(set(record["imports"]))[:100]
    record["note"] = "AST observations only; dynamic imports, data flow, and behavioral equivalence are not established"
    return record


def inspect(store, repository, training_entries, evaluation_entries=(), refresh=False):
    from .core import git
    repo = Path(repository).expanduser().resolve()
    baseline = git(repo, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    if repo == store.root or repo in store.root.parents:
        raise HarnessError("Keep project state outside the training repository")
    if not training_entries:
        raise HarnessError("Declare at least one training entry point")
    training = [_entry(repo, item) for item in training_entries]
    evaluation = [_entry(repo, item) for item in evaluation_entries]
    overlap = sorted(str(p) for p in set(training) & set(evaluation))
    missing = [str(p) for p in training + evaluation if not p.is_file()]
    finding = "split-required" if overlap else "separate-entrypoints" if evaluation and not missing else "uncertain"
    analysis = {
        "repository": str(repo), "baseline": baseline, "at": now(),
        "training_entries": [str(p) for p in training], "evaluation_entries": [str(p) for p in evaluation],
        "finding": finding, "shared_entries": overlap, "missing_entries": missing,
        "observations": [_inspect_file(p) for p in dict.fromkeys(training + evaluation)],
        "dirty_source": bool(git(repo, "status", "--porcelain").strip()),
        "limits": "Read-only static inspection, not an automatic refactor or proof of evaluator independence",
        "plan": [
            "Preserve the original training entry and record its baseline; keep user edits intact.",
            "If scoring shares mutable training code, extract a frozen scorer and expose checkpoint/inference or prediction export boundaries.",
            "Keep development validation/checkpoint selection explicit; never silently change its semantics.",
            "Place reference labels outside candidate-writable source; redirect checkpoints/logs to declared output roots.",
            "For a required split, compare before/after prediction exports on the same examples before approval.",
            "Review paths, metric/data protocol, environment, budgets, seeds and promotion policy with the user.",
        ],
    }
    identifier = project_id(repo)
    path = store.root / "projects" / identifier
    path.mkdir(parents=True, exist_ok=True)
    with locked(path / "project.lock"):
        if (path / "state.json").exists():
            if not refresh:
                raise HarnessError("Project already registered; use --refresh for a new assessment, invalidating its approval")
            history = path / "history" / ("assessment-" + uuid.uuid4().hex[:12])
            history.mkdir(parents=True)
            save(history / "state.json", load(path / "state.json"))
            save(history / "analysis.json", load(path / "analysis.json"))
        save(path / "analysis.json", analysis)
        (path / "DECOUPLING.md").write_text(
            "# Decoupling assessment\n\nFinding: **%s**.\n\n%s\n\n%s\n\n"
            "Static observations do not prove independence. No source files were changed and no training was launched.\n"
            % (finding, analysis["limits"], "\n".join("%s. %s" % (i + 1, step) for i, step in enumerate(analysis["plan"]))), encoding="utf-8",
        )
        save(path / "state.json", {"id": identifier, "repository": str(repo), "stage": "assessed", "revision": None, "created_at": now()})
    return {**state(store, identifier), "analysis": analysis, "decoupling_plan": str(path / "DECOUPLING.md")}


def review_digest(revision):
    return hashlib.sha256(canonical(load(revision / "spec.json")) + b"\0" + (revision / "BOUNDARIES.md").read_bytes()).hexdigest()


def _boundaries(spec):
    contract = spec["contract"]
    return "\n".join([
        "# Project boundary specification", "", "**Awaiting explicit user review. This document does not authorize itself.**", "",
        "## Source and decoupling", "",
        "Repository: `%s`" % spec["repository"], "Baseline: `%s`" % contract["source"]["baseline"],
        "Initial assessment: `%s`" % spec["decoupling"]["finding"],
        "A before/after prediction comparison is required: `%s`." % spec["decoupling"]["comparison_required"], "",
        "Keep existing training behavior unless explicitly proposed as an experiment. Shared scoring code must be separated before mutable training is permitted.", "",
        "## Agent edits", "", "Allowed paths:", "",
        *["- `%s`" % p for p in contract["source"]["allowed_paths"]], "",
        "Protected paths (deny takes precedence over allow):", "",
        *(["- `%s`" % p for p in contract["source"]["protected_paths"]] or ["- All paths outside the allowlist remain protected."]), "",
        "## Fixed evaluation and execution", "",
        "Training argv: `%s`" % contract["training"]["argv"],
        "Inference argv: `%s`" % contract["training"].get("inference_argv", "combined export; separately frozen scoring is still required"),
        "Metric: `%s` (%s)." % (contract["evaluation"]["metric"], contract["evaluation"]["direction"]),
        "Reference: `%s` (SHA-256 `%s`)." % (spec["immutable_inputs"]["reference"]["path"], spec["immutable_inputs"]["reference"]["sha256"]),
        "Trusted scorer: `%s` (SHA-256 `%s`)." % (spec["immutable_inputs"]["evaluator"]["path"], spec["immutable_inputs"]["evaluator"]["sha256"]),
        "Evaluation inputs: `%s` (SHA-256 `%s`)." % (spec["immutable_inputs"]["inputs"]["path"], spec["immutable_inputs"]["inputs"]["sha256"]),
        "Inspect the exact data/split and scoring semantics before approval. Python package paths: `%s`." % contract["training"].get("python_paths", []),
        "Execution: `%s`" % contract["execution"], "",
        "## Bounded exploration", "",
        "Iteration policy: `%s`" % spec["iteration_policy"],
        "Limits apply to this reviewed revision. Every reserved candidate counts, including failures and cancellations; no automatic refunds.",
        "Prepared and unresolved/orphaned candidates occupy active slots. An accepted candidate stops further exploration when stop_on_acceptance is true.",
        "Each candidate must declare changed factors; actual changed files and its patch are recorded separately.",
        "Increasing limits or restarting an exhausted revision requires a fresh specification and user review.", "",
        "## Acceptance and promotion", "",
        "Acceptance: `%s`" % contract["acceptance"],
        "This is development acceptance, without a confirmation/repeated-testing guarantee. Failed/missing observations cannot be silently removed.",
        "Promotion is a separate explicit action; destination baseline drift requires revalidation.", "",
        "## Human review checklist", "",
        "- Are training, inference and trusted scoring boundaries appropriate, including checkpoint selection?",
        "- Are the allowed/protected paths, reference split, scoring formula and immutable input files correct?",
        "- Are the environment, seeds, command/total time budgets, candidate/active limits and stopping/promotion rules acceptable?",
        "- Review the exact spec digest with the user. The coding agent must not approve on the user's behalf.", "",
        "The approval record is a local operator attestation. It does not authenticate a human against an unrestricted same-user process.", "",
    ])


def draft(store, identifier, config_path, protected_paths=(), max_experiments=1, max_active=1, stop_on_acceptance=True):
    from .core import git, in_scope, validate
    from .controls import policy
    iteration_policy = policy(max_experiments, max_active, stop_on_acceptance)
    path = directory(store, identifier)
    with locked(path / "project.lock"):
        current = load(path / "state.json")
        config_path = Path(config_path).resolve()
        contract = validate(load(config_path), config_path.parent)
        if contract["source"]["repository"] != current["repository"]:
            raise HarnessError("Contract repository differs from assessed project")
        repo = Path(current["repository"])
        if git(repo, "status", "--porcelain").strip():
            raise HarnessError("Commit or separately preserve source edits before drafting; no user files were changed")
        if git(repo, "rev-parse", "HEAD").decode().strip() != contract["source"]["baseline"]:
            raise HarnessError("Draft must describe the current committed baseline")
        analysis = load(path / "analysis.json")
        if analysis["missing_entries"]:
            raise HarnessError("Assessment has missing entry points; correct the project setup before drafting")
        evaluator = Path(contract["evaluation"]["evaluator"])
        if str(evaluator) in analysis["training_entries"]:
            raise HarnessError("Trusted scorer still shares a training entry; separate it before drafting")
        protected = list(dict.fromkeys([*contract["source"].get("protected_paths", []), *protected_paths]))
        if repo in evaluator.parents:
            protected.append(evaluator.relative_to(repo).as_posix())
        contract["source"]["protected_paths"] = sorted(set(protected))
        # Revalidate the final scope including added deny paths.
        contract = validate(contract, config_path.parent)
        tracked = list(filter(None, git(repo, "ls-files", "-z").decode().split("\0")))
        protected_files = {p: digest(repo / p) for p in tracked if in_scope(p, contract["source"]["protected_paths"]) and (repo / p).is_file()}
        immutable = {key: {"path": contract[section][field], "sha256": digest(contract[section][field])}
                     for key, section, field in [("inputs", "training", "inputs"), ("reference", "evaluation", "reference"), ("evaluator", "evaluation", "evaluator")]}
        spec = {
            "schema_version": 2, "project": identifier, "repository": str(repo), "contract": contract,
            "iteration_policy": iteration_policy,
            "analysis_sha256": digest(path / "analysis.json"), "protected_files": protected_files, "immutable_inputs": immutable,
            "decoupling": {"finding": analysis["finding"], "comparison_required": analysis["finding"] == "split-required", "original_baseline": analysis["baseline"]},
        }
        revision_name = "revision-" + uuid.uuid4().hex[:12]
        revision = path / "revisions" / revision_name
        revision.mkdir(parents=True)
        save(revision / "spec.json", spec)
        (revision / "BOUNDARIES.md").write_text(_boundaries(spec), encoding="utf-8")
        current.update(stage="awaiting_review", revision=revision_name, approval=None, updated_at=now())
        save(path / "state.json", current)
    return state(store, identifier)


def _revision(store, identifier):
    path = directory(store, identifier)
    current = load(path / "state.json")
    if not current.get("revision"):
        raise HarnessError("Draft a boundary specification first")
    if not re.fullmatch(r"revision-[0-9a-f]{12}", current["revision"]):
        raise HarnessError("Invalid project revision")
    return path, current, path / "revisions" / current["revision"]


def _check_inputs(spec):
    from .core import git
    expected_inputs = {
        "inputs": spec["contract"]["training"]["inputs"],
        "reference": spec["contract"]["evaluation"]["reference"],
        "evaluator": spec["contract"]["evaluation"]["evaluator"],
    }
    if spec["repository"] != spec["contract"]["source"]["repository"] or any(
        spec["immutable_inputs"][name]["path"] != expected for name, expected in expected_inputs.items()
    ):
        raise HarnessError("Specification and frozen input references disagree; generate a new draft")
    repo = Path(spec["repository"])
    if git(repo, "rev-parse", "HEAD").decode().strip() != spec["contract"]["source"]["baseline"]:
        raise HarnessError("Approved source baseline changed; draft and review a new specification")
    if git(repo, "status", "--porcelain").strip():
        raise HarnessError("Original source has uncommitted edits; preserve/commit them before project iteration")
    for name, item in spec["immutable_inputs"].items():
        p = Path(item["path"])
        if not p.is_file() or digest(p) != item["sha256"]:
            raise HarnessError("Fixed " + name + " changed; a new user review is required")
    for name, expected in spec["protected_files"].items():
        p = repo / name
        if not p.is_file() or digest(p) != expected:
            raise HarnessError("Protected source changed: " + name)


def compare_split(store, identifier, before_path, after_path):
    from .scoring import records
    path, current, revision = _revision(store, identifier)
    with locked(path / "project.lock"):
        if load(path / "state.json")["revision"] != current["revision"]:
            raise HarnessError("Project revision changed")
        if current["stage"] != "awaiting_review":
            raise HarnessError("Prediction comparison belongs to the pre-approval review stage")
        _check_inputs(load(revision / "spec.json"))
        before, after = Path(before_path).resolve(), Path(after_path).resolve()
        for p in (before, after):
            if not p.is_file() or p.stat().st_size > 10 * 1024 * 1024:
                raise HarnessError("Comparison inputs must be regular JSONL files of at most 10 MiB")
        left, right = records(before), records(after)
        # Exact structured equality; do not silently tolerate changed outputs.
        equivalent = canonical(left) == canonical(right)
        comparison_id = "comparison-" + uuid.uuid4().hex[:12]
        evidence = revision / comparison_id
        evidence.mkdir()
        (evidence / "before.jsonl").write_bytes(before.read_bytes())
        (evidence / "after.jsonl").write_bytes(after.read_bytes())
        record = {
            "at": now(), "spec_digest": review_digest(revision), "equivalent": equivalent,
            "before_count": len(left), "after_count": len(right),
            "before_sha256": digest(evidence / "before.jsonl"), "after_sha256": digest(evidence / "after.jsonl"),
            "evidence": comparison_id,
            "limits": "Compares user-supplied prediction exports only; execution provenance and training equivalence are not certified",
        }
        save(evidence / "comparison.json", record)
        save(revision / "comparison.json", record)
    return record


def _check_comparison(revision, spec):
    if not spec["decoupling"]["comparison_required"]:
        return None
    if not (revision / "comparison.json").is_file():
        raise HarnessError("Required split has no before/after prediction comparison")
    record = load(revision / "comparison.json")
    if not record["equivalent"] or record["spec_digest"] != review_digest(revision):
        raise HarnessError("Split comparison failed or belongs to a different specification")
    if not re.fullmatch(r"comparison-[0-9a-f]{12}", record["evidence"]):
        raise HarnessError("Invalid comparison evidence path")
    evidence = revision / record["evidence"]
    for name in ("before", "after"):
        if digest(evidence / (name + ".jsonl")) != record[name + "_sha256"]:
            raise HarnessError("Split comparison evidence changed")
    return digest(revision / "comparison.json")


def approve(store, identifier, acknowledged_digest, reviewer):
    path, current, revision = _revision(store, identifier)
    with locked(path / "project.lock"):
        if load(path / "state.json")["revision"] != current["revision"]:
            raise HarnessError("Project revision changed")
        expected = review_digest(revision)
        if acknowledged_digest != expected:
            raise HarnessError("Review digest differs; read the current specification with the user")
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise HarnessError("An explicit reviewer/operator attestation is required")
        spec = load(revision / "spec.json")
        if digest(path / "analysis.json") != spec["analysis_sha256"]:
            raise HarnessError("Project assessment changed; draft and review a new specification")
        _check_inputs(spec)
        comparison = _check_comparison(revision, spec)
        record = {"at": now(), "reviewer": reviewer, "spec_digest": expected, "comparison_sha256": comparison,
                  "attestation": "Operator explicitly acknowledged this exact specification; this is not identity authentication"}
        save(revision / "approval.json", record)
        current.update(stage="approved", approval=record, updated_at=now())
        save(path / "state.json", current)
    return state(store, identifier)


def assert_approved(store, identifier, expected_digest=None):
    path, current, revision = _revision(store, identifier)
    if current["stage"] != "approved" or not (revision / "approval.json").is_file():
        raise HarnessError("Project boundaries are awaiting user review; iteration is blocked")
    approval = load(revision / "approval.json")
    actual = review_digest(revision)
    if actual != approval["spec_digest"] or (expected_digest is not None and actual != expected_digest):
        raise HarnessError("Approved specification changed; a new user review is required")
    spec = load(revision / "spec.json")
    if digest(path / "analysis.json") != spec["analysis_sha256"]:
        raise HarnessError("Project assessment changed; a new user review is required")
    _check_inputs(spec)
    if _check_comparison(revision, spec) != approval.get("comparison_sha256"):
        raise HarnessError("Split comparison changed after approval")
    return spec, {"project": identifier, "revision": current["revision"], "spec_digest": actual}


def authorize_contract(store, contract):
    identifier = project_id(contract["source"]["repository"])
    if not (store.root / "projects" / identifier / "state.json").is_file():
        return None  # Unregistered low-level experiments remain backwards compatible.
    spec, context = assert_approved(store, identifier)
    expected, proposed = copy.deepcopy(spec["contract"]), copy.deepcopy(contract)
    expected.pop("hypothesis")
    proposed.pop("hypothesis")
    if canonical(expected) != canonical(proposed):
        raise HarnessError("Experiment changes the approved contract; draft and review a new specification")
    return context


def iterate(store, identifier, hypothesis, patch_path=None, factors=None):
    from .core import create
    _, _, revision = _revision(store, identifier)
    spec, _ = assert_approved(store, identifier)
    contract = copy.deepcopy(spec["contract"])
    contract["hypothesis"] = hypothesis
    request = revision / "requests" / (uuid.uuid4().hex + ".json")
    save(request, contract)
    return create(store, request, patch_path, factors=factors)
