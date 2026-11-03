"""Bounded exploration within a reviewed revision; no LLM or research dependency."""

from contextlib import contextmanager
import re
import uuid

from .storage import HarnessError, load, locked, now, save


def policy(max_experiments=1, max_active=1, stop_on_acceptance=True):
    for name, value in (("max_experiments", max_experiments), ("max_active", max_active)):
        if type(value) is not int or not 1 <= value <= 1000:
            raise HarnessError(name + " must be an integer in [1, 1000]")
    if max_active > max_experiments or type(stop_on_acceptance) is not bool:
        raise HarnessError("max_active must not exceed max_experiments; stop_on_acceptance must be boolean")
    return {"max_experiments": max_experiments, "max_active": max_active,
            "stop_on_acceptance": stop_on_acceptance}


def _snapshot(store, path, revision, spec):
    from .core import TERMINAL
    entries = load(revision / "iterations.json") if (revision / "iterations.json").exists() else []
    states = []
    for item in entries:
        identifier = item["id"]
        if not re.fullmatch(r"exp-[0-9a-f]{16}", identifier):
            raise HarnessError("Invalid iteration reservation")
        recorded = store.runs / identifier / "state.json"
        status = load(recorded)["status"] if recorded.is_file() else "reserved"
        states.append({**item, "status": status})
    active = [item["id"] for item in states if item["status"] not in TERMINAL or item["status"] == "orphaned"]
    prior_active = []
    for ledger in sorted((path / "revisions").glob("*/iterations.json")):
        if ledger.parent == revision:
            continue
        for item in load(ledger):
            identifier = item["id"]
            if not re.fullmatch(r"exp-[0-9a-f]{16}", identifier):
                raise HarnessError("Invalid prior iteration reservation")
            recorded = store.runs / identifier / "state.json"
            status = load(recorded)["status"] if recorded.is_file() else "reserved"
            if status not in TERMINAL or status == "orphaned":
                prior_active.append({"id": identifier, "revision": ledger.parent.name, "status": status})
                active.append(identifier)
    paused = load(path / "control.json") if (path / "control.json").is_file() else {"paused": False}
    limits = spec.get("iteration_policy")
    return {"policy": limits, "used": len(states), "remaining": max(0, limits["max_experiments"] - len(states)) if limits else None,
            "active": active, "prior_active": prior_active, "experiments": states, "operator_control": paused}


def _reasons(snapshot, creating=False, promoting=False):
    reasons = []
    limits = snapshot["policy"]
    if snapshot["operator_control"]["paused"]:
        reasons.append("Project is paused: " + snapshot["operator_control"].get("reason", "operator request"))
    if creating and not limits:
        reasons.append("Legacy specification has no iteration policy; draft and review a bounded revision before new candidates")
    if limits:
        if not promoting and limits["stop_on_acceptance"] and any(
            item["status"] in {"accepted", "promoted"} for item in snapshot["experiments"]
        ):
            reasons.append("stop_on_acceptance reached; no further exploration under this revision")
        if creating and snapshot["used"] >= limits["max_experiments"]:
            reasons.append("Iteration budget exhausted (max_experiments)")
        if creating and len(snapshot["active"]) >= limits["max_active"]:
            reasons.append("Active candidate limit reached (max_active); finish or cancel the recorded candidate first")
    return reasons


def reserve(store, context, identifier, hypothesis, factors):
    from .onboarding import assert_approved, directory
    path = directory(store, context["project"])
    with locked(path / "project.lock"):
        spec, current = assert_approved(store, context["project"], context["spec_digest"])
        revision = path / "revisions" / current["revision"]
        snapshot = _snapshot(store, path, revision, spec)
        reasons = _reasons(snapshot, creating=True)
        if reasons:
            raise HarnessError("; ".join(reasons))
        if not isinstance(factors, list) or not factors or not all(isinstance(x, str) and x.strip() for x in factors):
            raise HarnessError("Declare changed factors with iterate --factor before reserving an experiment")
        entry = {"id": identifier, "reserved_at": now(), "hypothesis": hypothesis, "factors": factors}
        entries = load(revision / "iterations.json") if (revision / "iterations.json").exists() else []
        save(revision / "iterations.json", [*entries, entry])
        return entry


@contextmanager
def permit(store, identifier, promoting=False):
    """Serialize dispatch/promotion against pause and candidate reservations."""
    from .onboarding import authorize_contract, directory, project_id
    run = store.run(identifier)
    contract = load(run / "contract.json")
    path = store.root / "projects" / project_id(contract["source"]["repository"])
    if not (path / "state.json").is_file():
        yield
        return
    path = directory(store, path.name)
    with locked(path / "project.lock"):
        context = authorize_contract(store, contract)
        if not (run / "project.json").is_file():
            raise HarnessError("Experiment predates project review; create an experiment bound to the approved revision")
        revision = path / "revisions" / context["revision"]
        spec = load(revision / "spec.json")
        snapshot = _snapshot(store, path, revision, spec)
        reasons = _reasons(snapshot, promoting=promoting)
        if spec.get("iteration_policy") and identifier not in {item["id"] for item in snapshot["experiments"]}:
            reasons.append("Experiment has no reservation in the approved iteration budget")
        if reasons:
            raise HarnessError("; ".join(reasons))
        yield


def status(store, project):
    from .onboarding import _revision, assert_approved, directory
    path = directory(store, project)
    with locked(path / "project.lock"):
        _, _, revision = _revision(store, project)
        spec = load(revision / "spec.json")
        snapshot = _snapshot(store, path, revision, spec)
        reasons = _reasons(snapshot, creating=True)
        try:
            assert_approved(store, project)
        except HarnessError as error:
            reasons.insert(0, str(error))
        return {**snapshot, "can_create": not reasons, "blocked_reasons": reasons}


def set_paused(store, project, paused, reason):
    from .onboarding import directory
    if not isinstance(reason, str) or not reason.strip():
        raise HarnessError("Record the operator's reason for pausing/resuming")
    path = directory(store, project)
    with locked(path / "project.lock"):
        record = {"paused": paused, "reason": reason, "at": now(),
                  "effect": "Blocks new dispatch and promotion; already running experiments continue. Use cancel for a specific job."}
        save(path / "control-history" / (uuid.uuid4().hex + ".json"), record)
        save(path / "control.json", record)
    return record
