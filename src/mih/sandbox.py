"""The macOS profile constrains child processes, not the calling agent."""

import json
import os
from pathlib import Path
import platform
import shutil
import sys

from .storage import HarnessError


def resolve_mode(requested):
    if requested == "auto":
        if platform.system() == "Darwin" and Path("/usr/bin/sandbox-exec").exists():
            return "macos-sandbox"
        raise HarnessError("No enforced local sandbox on this platform; explicitly select trusted-local for trusted code")
    if requested == "macos-sandbox":
        if platform.system() != "Darwin" or not Path("/usr/bin/sandbox-exec").exists():
            raise HarnessError("macos-sandbox requires macOS sandbox-exec")
        return requested
    if requested == "trusted-local":
        return requested
    raise HarnessError("Unknown isolation mode")


def wrap(argv, mode, writable, protected):
    if mode == "trusted-local":
        return argv
    rules = ["(version 1)", "(allow default)", "(deny network*)", "(deny signal)", "(deny file-write*)",
             '(allow file-write* (literal "/dev/null"))']
    for path in writable:
        rules.append("(allow file-write* (subpath %s))" % json.dumps(str(Path(path).resolve())))
    for path in protected:
        resolved = Path(path).resolve()
        rules.append("(deny file-read* (subpath %s))" % json.dumps(str(resolved)))
        # The default write denial already covers paths outside writable roots.
        # Add an explicit denial only for protected entries inside a writable root
        # (e.g. a worktree's .git file), so preopened log FDs can be writable.
        if any(resolved == Path(root).resolve() or Path(root).resolve() in resolved.parents for root in writable):
            rules.append("(deny file-write* (subpath %s))" % json.dumps(str(resolved)))
    return ["/usr/bin/sandbox-exec", "-p", " ".join(rules), *argv]


def environment(temporary, seed, python_paths=()):
    # Credentials and the caller's Python import path are deliberately not inherited.
    result = {
        "PATH": os.defpath + ":/opt/homebrew/bin:/usr/local/bin",
        "HOME": str(temporary), "TMPDIR": str(temporary),
        "LANG": "en_US.UTF-8", "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": str(seed), "MIH_SEED": str(seed),
        "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
    }
    if python_paths:
        result["PYTHONPATH"] = os.pathsep.join(python_paths)
    return result


def expand(argv, values):
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
        raise HarnessError("Commands must be nonempty argv arrays; shell strings are not supported")
    result = []
    for argument in argv:
        for key, value in values.items():
            argument = argument.replace("{" + key + "}", str(value))
        result.append(argument)
    if result[0] == "python":
        result[0] = sys.executable
    elif not os.path.isabs(result[0]):
        executable = shutil.which(result[0], path=os.defpath + ":/opt/homebrew/bin:/usr/local/bin")
        if not executable:
            raise HarnessError("Executable not found: " + result[0])
        result[0] = executable
    return result
