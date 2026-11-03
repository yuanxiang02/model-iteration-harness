#!/usr/bin/env python3
"""Create and check file-based skill handoffs; no model calls or training."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid


STAGES = {
    "research": ({"candidate_options", "insufficient_evidence"},
                 {"sources": list, "candidates": list, "recommendation": str}),
    "novelty": ({"overlap_found", "distinct_candidate", "insufficient_evidence"},
                {"claims": list, "closest_sources": list, "search_scope": str}),
    "review": ({"changes_requested", "ready_for_experiment", "claims_limited", "insufficient_evidence"},
               {"reviewers": list, "findings": list, "disagreements": list, "review_mode": str}),
    "iteration": ({"submitted", "awaiting_boundary_review", "accepted_development", "rejected", "inconclusive", "failed", "insufficient_evidence"},
                  {"project_id": (str, type(None)), "experiment_id": (str, type(None)), "runtime_report": (str, type(None))}),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.sha256(stream.read()).hexdigest()


def read(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key: " + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("non-finite JSON value: " + value)
    return json.loads(Path(path).read_text(), object_pairs_hook=pairs, parse_constant=invalid)


def fields(value, expected, label):
    require(isinstance(value, dict), label + " must be an object")
    for key, kind in expected.items():
        require(key in value and isinstance(value[key], kind), label + "." + key + " has a missing/invalid type")


def reference(item, root=None):
    fields(item, {"path": str, "sha256": str}, "file reference")
    require(bool(re.fullmatch(r"[0-9a-f]{64}", item["sha256"])), "invalid SHA-256")
    raw = Path(item["path"])
    if root is None:
        require(raw.is_absolute(), "input path must be absolute")
        path = raw.resolve()
    else:
        require(not raw.is_absolute(), "artifact path must be relative")
        path = (root / raw).resolve()
        require(root in path.parents, "artifact escapes run directory")
    require(path.is_file(), "missing evidence file: " + str(path))
    require(digest(path) == item["sha256"], "evidence hash mismatch: " + str(path))
    return item["path"]


def check_request(request):
    fields(request, {"interface_version": str, "run_id": str, "stage": str,
                     "goal": str, "project": dict, "constraints": dict, "inputs": list}, "request")
    require(request["interface_version"] == "1", "unsupported interface version")
    require(request["stage"] in STAGES, "unknown stage")
    require(bool(request["run_id"].strip()) and bool(request["goal"].strip()), "empty run ID or goal")
    project = request["project"]
    fields(project, {"repository": str, "baseline_commit": str, "dirty": bool}, "project")
    require(Path(project["repository"]).is_absolute(), "repository must be absolute")
    require(bool(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", project["baseline_commit"])), "invalid baseline commit")
    for item in request["inputs"]:
        reference(item)
    if request["stage"] == "review":
        settings = request["constraints"]
        require(settings.get("review_kind") in {"proposal", "results"}, "review_kind must be proposal or results")
        require(type(settings.get("required_reviewers")) is int and settings["required_reviewers"] > 0,
                "required_reviewers must be a positive integer")


def check_review(request, result, artifacts):
    payload = result["payload"]
    mode = payload["review_mode"]
    require(mode in {"multi_agent", "self_review", "unavailable"}, "invalid review mode")
    ids, agents, completed = set(), set(), []
    for reviewer in payload["reviewers"]:
        fields(reviewer, {"id": str, "role": str, "status": str, "model": str,
                          "agent_id": (str, type(None)), "prompt_path": (str, type(None)),
                          "response_path": (str, type(None))}, "reviewer")
        require(reviewer["id"] and reviewer["id"] not in ids, "duplicate/empty reviewer ID")
        ids.add(reviewer["id"])
        require(reviewer["status"] in {"completed", "failed", "unavailable"}, "invalid reviewer status")
        if reviewer["status"] == "completed":
            require(reviewer["prompt_path"] in artifacts and reviewer["response_path"] in artifacts,
                    "completed reviewer must link hashed prompt and response")
            completed.append(reviewer)
            if mode == "multi_agent":
                require(reviewer["agent_id"] and reviewer["agent_id"] not in agents,
                        "multi-agent review requires distinct recorded agent IDs")
                agents.add(reviewer["agent_id"])
    if mode == "multi_agent":
        require(request["constraints"].get("delegation_authorized") is True,
                "multi-agent request must record delegation authorization")
        require(len(completed) >= 2, "multi-agent mode requires at least two completed reviewers")
    for finding in payload["findings"]:
        fields(finding, {"id": str, "severity": str, "status": str, "evidence": str}, "finding")
        require(finding["severity"] in {"blocking", "major", "minor"}, "invalid finding severity")
        require(finding["status"] in {"open", "resolved"}, "invalid finding status")
    if result["decision"] == "ready_for_experiment":
        require(result["status"] == "completed" and mode == "multi_agent", "ready requires completed independent review")
        require(request["constraints"]["review_kind"] == "proposal", "ready decision is for proposals")
        require(len(completed) >= request["constraints"]["required_reviewers"], "missing required reviewers")
        require(not any(f["severity"] == "blocking" and f["status"] == "open" for f in payload["findings"]),
                "unresolved blocking finding")


def check(directory, request_only=False):
    root = Path(directory).resolve()
    request = read(root / "request.json")
    check_request(request)
    if request_only:
        return {"valid": True, "stage": request["stage"], "scope": "request"}
    result = read(root / "result.json")
    fields(result, {"interface_version": str, "run_id": str, "stage": str,
                    "request_sha256": str, "status": str, "decision": str, "summary": str,
                    "artifacts": list, "limitations": list, "next_actions": list, "payload": dict}, "result")
    for key in ("interface_version", "run_id", "stage"):
        require(result[key] == request[key], "request/result mismatch: " + key)
    require(result["request_sha256"] == digest(root / "request.json"), "request hash mismatch")
    require(result["status"] in {"completed", "needs_input", "unavailable", "failed"}, "invalid result status")
    require(result["decision"] in STAGES[request["stage"]][0], "invalid stage decision")
    require(result["status"] == "completed" or result["decision"] == "insufficient_evidence",
            "incomplete result cannot have a positive decision")
    require(all(isinstance(x, str) for x in result["limitations"] + result["next_actions"]), "invalid text list")
    require(bool(result["artifacts"]), "at least one evidence artifact is required")
    artifacts = set()
    for item in result["artifacts"]:
        name = reference(item, root)
        require(name not in artifacts and name not in {"request.json", "result.json"}, "duplicate or reserved artifact")
        artifacts.add(name)
    fields(result["payload"], STAGES[request["stage"]][1], "payload")
    if request["stage"] == "review":
        check_review(request, result, artifacts)
    elif request["stage"] == "research" and result["decision"] == "candidate_options":
        require(bool(result["payload"]["candidates"]), "candidate decision needs candidate evidence")
    elif request["stage"] == "novelty" and result["decision"] != "insufficient_evidence":
        require(bool(result["payload"]["claims"]) and bool(result["payload"]["closest_sources"]),
                "novelty decision needs claims and prior-work evidence")
    elif request["stage"] == "iteration":
        payload = result["payload"]
        if result["decision"] in {"accepted_development", "rejected", "inconclusive", "failed"}:
            require(bool(payload["experiment_id"]) and payload["runtime_report"] in artifacts,
                    "iteration conclusion needs an experiment ID and hashed runtime report")
    return {"valid": True, "stage": request["stage"], "scope": "packet", "scientific_verdict_verified": False}


def initialize(directory, stage, repository, goal):
    root = Path(directory).resolve()
    repo = Path(repository).resolve(strict=True)
    require(not (root == repo or repo in root.parents), "run directory must be outside training repository")
    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
    request = {"interface_version": "1", "run_id": "run-" + uuid.uuid4().hex,
               "stage": stage, "goal": goal,
               "project": {"repository": str(repo), "baseline_commit": git("rev-parse", "HEAD"),
                           "dirty": bool(git("status", "--porcelain"))},
               "constraints": {}, "inputs": []}
    if stage == "review":
        request["constraints"] = {"review_kind": "proposal", "required_reviewers": 2, "delegation_authorized": False}
    check_request(request)
    root.mkdir(parents=True, exist_ok=False)
    (root / "request.json").write_text(json.dumps(request, indent=2, ensure_ascii=False) + "\n")
    return {"run_directory": str(root), "request_sha256": digest(root / "request.json")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("directory")
    init.add_argument("--stage", choices=STAGES, required=True)
    init.add_argument("--repository", required=True)
    init.add_argument("--goal", required=True)
    validate = commands.add_parser("check")
    validate.add_argument("directory")
    validate.add_argument("--request-only", action="store_true")
    hashing = commands.add_parser("hash")
    hashing.add_argument("file")
    args = parser.parse_args()
    try:
        if args.command == "init":
            result = initialize(args.directory, args.stage, args.repository, args.goal)
        elif args.command == "hash":
            result = {"sha256": digest(args.file)}
        else:
            result = check(args.directory, args.request_only)
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
