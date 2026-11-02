"""Machine-readable CLI for agents, humans, and scripts."""

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from . import core, onboarding
from .storage import HarnessError, Store, load


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mih", description="Local model iteration harness")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--state", default=".mih", help="Harness state directory; keep it outside the training repository")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("validate", help="Validate and resolve a contract without running training")
    check.add_argument("contract")
    create = commands.add_parser("create", help="Freeze a contract and create baseline/candidate worktrees")
    create.add_argument("contract")
    create.add_argument("--patch")
    for name in ("submit", "status", "report", "cancel", "recover"):
        item = commands.add_parser(name)
        item.add_argument("id")
    wait = commands.add_parser("wait", help="Wait in ordinary Python; no model calls")
    wait.add_argument("id")
    wait.add_argument("--timeout", type=float, default=60)
    promote = commands.add_parser("promote", help="Check or explicitly apply an accepted development patch")
    promote.add_argument("id")
    promote.add_argument("--apply", action="store_true")
    commands.add_parser("list")
    project = commands.add_parser("project", help="Assess decoupling, draft boundaries, and record user review")
    stages = project.add_subparsers(dest="project_command", required=True)
    inspect = stages.add_parser("inspect", help="Read-only AST observations and a decoupling plan; no training")
    inspect.add_argument("repository")
    inspect.add_argument("--train", action="append", required=True, dest="training_entries")
    inspect.add_argument("--eval", action="append", default=[], dest="evaluation_entries")
    inspect.add_argument("--refresh", action="store_true", help="Archive the prior assessment and invalidate its approval")
    draft = stages.add_parser("draft", help="Generate a versioned specification and BOUNDARIES.md for user review")
    draft.add_argument("id")
    draft.add_argument("contract")
    draft.add_argument("--protect", action="append", default=[])
    project_status = stages.add_parser("status")
    project_status.add_argument("id")
    compare = stages.add_parser("compare-split", help="Compare user-supplied before/after prediction exports exactly")
    compare.add_argument("id")
    compare.add_argument("--before", required=True)
    compare.add_argument("--after", required=True)
    approve = stages.add_parser("approve", help="Record explicit operator acknowledgment; never self-approve as an agent")
    approve.add_argument("id")
    approve.add_argument("--digest", required=True)
    approve.add_argument("--reviewer", required=True)
    iterate = commands.add_parser("iterate", help="Create a candidate under an approved project specification")
    iterate.add_argument("id")
    iterate.add_argument("--hypothesis", required=True)
    iterate.add_argument("--patch")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            path = Path(args.contract).resolve()
            result = {"valid": True, "resolved_contract": core.validate(load(path), path.parent)}
        else:
            store = Store(args.state)
            if args.command == "project":
                if args.project_command == "inspect":
                    result = onboarding.inspect(store, args.repository, args.training_entries, args.evaluation_entries, args.refresh)
                elif args.project_command == "draft":
                    result = onboarding.draft(store, args.id, args.contract, args.protect)
                elif args.project_command == "approve":
                    result = onboarding.approve(store, args.id, args.digest, args.reviewer)
                elif args.project_command == "compare-split":
                    result = onboarding.compare_split(store, args.id, args.before, args.after)
                else:
                    result = onboarding.state(store, args.id)
            elif args.command == "iterate":
                result = onboarding.iterate(store, args.id, args.hypothesis, args.patch)
            elif args.command == "create":
                result = core.create(store, args.contract, args.patch)
            elif args.command == "submit":
                result = core.submit(store, args.id)
            elif args.command == "status":
                result = core.status(store, args.id)
            elif args.command == "report":
                result = core.report(store, args.id)
            elif args.command == "wait":
                if args.timeout < 0:
                    raise HarnessError("timeout must be nonnegative")
                result = core.wait(store, args.id, args.timeout)
            elif args.command == "cancel":
                result = core.cancel(store, args.id)
            elif args.command == "recover":
                result = core.recover(store, args.id)
            elif args.command == "promote":
                result = core.promote(store, args.id, args.apply)
            else:
                result = [store.state(p.name) for p in sorted(store.runs.iterdir()) if (p / "state.json").is_file()]
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False))
    except (HarnessError, ValueError, KeyError, OSError, TypeError) as error:
        print(json.dumps({"error": str(error), "type": type(error).__name__}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
