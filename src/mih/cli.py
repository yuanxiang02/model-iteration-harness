"""Machine-readable CLI for agents, humans, and scripts."""

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from . import core
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
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            path = Path(args.contract).resolve()
            result = {"valid": True, "resolved_contract": core.validate(load(path), path.parent)}
        else:
            store = Store(args.state)
            if args.command == "create":
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
