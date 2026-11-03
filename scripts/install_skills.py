#!/usr/bin/env python3
"""Install controlled model iteration, optionally with research/review helpers."""

import argparse
import json
import os
from pathlib import Path
import shutil
import sys


CORE = ("model-iteration",)
ADDONS = ("mi-research", "mi-novelty", "mi-review")
NAMES = CORE + ADDONS


def install(destination, with_addons=False):
    source = Path(__file__).resolve().parents[1] / "skills"
    target = Path(destination).expanduser().resolve()
    selected = NAMES if with_addons else CORE
    for name in selected:
        if not (source / name / "SKILL.md").is_file():
            raise ValueError("missing bundled skill: " + name)
        if os.path.lexists(target / name):
            raise ValueError("existing skill will not be overwritten: " + str(target / name))
    target.mkdir(parents=True, exist_ok=True)
    copied = []
    try:
        for name in selected:
            shutil.copytree(source / name, target / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            copied.append(name)
    except OSError:
        # Preserve pre-existing entries; remove only directories created by us.
        for name in copied:
            shutil.rmtree(target / name)
        raise
    return {"destination": str(target), "installed": list(selected), "runtime_installed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    # This is the real Codex skill location; never change CODEX_HOME itself.
    default = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills"
    parser.add_argument("--dest", default=str(default))
    parser.add_argument("--with-addons", action="store_true", help="Also install optional research, novelty and review skills")
    args = parser.parse_args()
    try:
        print(json.dumps(install(args.dest, args.with_addons), indent=2))
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
