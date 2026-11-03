#!/usr/bin/env python3
"""Install the four-skill bundle without overwriting existing skills."""

import argparse
import json
import os
from pathlib import Path
import shutil
import sys


NAMES = ("model-iteration", "mi-research", "mi-novelty", "mi-review")


def install(destination):
    source = Path(__file__).resolve().parents[1] / "skills"
    target = Path(destination).expanduser().resolve()
    for name in NAMES:
        if not (source / name / "SKILL.md").is_file():
            raise ValueError("missing bundled skill: " + name)
        if os.path.lexists(target / name):
            raise ValueError("existing skill will not be overwritten: " + str(target / name))
    target.mkdir(parents=True, exist_ok=True)
    copied = []
    try:
        for name in NAMES:
            shutil.copytree(source / name, target / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            copied.append(name)
    except OSError:
        # Preserve pre-existing entries; remove only directories created by us.
        for name in copied:
            shutil.rmtree(target / name)
        raise
    return {"destination": str(target), "installed": list(NAMES), "runtime_installed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    # This is the real Codex skill location; never change CODEX_HOME itself.
    default = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills"
    parser.add_argument("--dest", default=str(default))
    args = parser.parse_args()
    try:
        print(json.dumps(install(args.dest), indent=2))
    except (OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
