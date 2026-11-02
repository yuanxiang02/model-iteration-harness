"""Fetch pinned MIT examples and run small, real training jobs through the harness.

No global packages are installed. Network access is only used by this preparation
script; candidate subprocesses run with the configured local isolation mode.
"""

import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mih import core
from mih.storage import HarnessError, Store, load, save

EXAMPLES = Path(__file__).resolve().parent


def download(item, cache):
    path = cache / item["sha256"]
    if not path.exists():
        request = urllib.request.Request(item["url"], headers={"User-Agent": "model-iteration-harness-example"})
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read(4 * 1024 * 1024 + 1)
        if len(payload) > 4 * 1024 * 1024 or hashlib.sha256(payload).hexdigest() != item["sha256"]:
            raise HarnessError("Upstream download hash mismatch or excessive size")
        path.write_bytes(payload)
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != item["sha256"]:
        raise HarnessError("Cached upstream hash mismatch")
    return payload


def jsonlines(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def fixtures(task):
    if task == "micrograd":
        points = [[x, y] for x in [-.9, -.3, .3, .9] for y in [-.8, -.2, .2, .8]]
        inputs = [{"id": "point-%s" % i, "features": point} for i, point in enumerate(points)]
        reference = [{"id": row["id"], "target": int(sum(row["features"]) > 0)} for row in inputs]
        return inputs, reference, {"steps": 1}, {"steps": 40}, "accuracy", "maximize", "Increase SGD steps from 1 to 40 under the same fixed data and evaluation protocol."
    if task == "simplebayes":
        examples = [
            ("good film", "positive"), ("great movie", "positive"),
            ("not bad film", "positive"), ("not terrible movie", "positive"),
            ("bad movie", "negative"), ("terrible film", "negative"),
            ("not good movie", "negative"), ("not great film", "negative"),
        ]
        inputs = [{"id": "text-%s" % i, "text": text} for i, (text, _) in enumerate(examples)]
        reference = [{"id": row["id"], "target": examples[i][1]} for i, row in enumerate(inputs)]
        return inputs, reference, {"bigrams": False}, {"bigrams": True}, "accuracy", "maximize", "Add adjacent-word features to the same tiny naive Bayes training corpus."
    names = ["alma", "amelie", "lilia", "nella"]
    inputs, reference = [], []
    for name in names:
        for pos, target in enumerate(name):
            key = "char-%s" % len(inputs)
            inputs.append({"id": key, "context": name[:pos]})
            reference.append({"id": key, "target": target})
    return inputs, reference, {"steps": 1}, {"steps": 40}, "nll", "minimize", "Increase an 8-hidden-unit PyTorch GRU from 1 to 40 training steps under the same text protocol."


def torch_environment(requested=None, extra_paths=()):
    candidates = [requested] if requested else [sys.executable, shutil.which("python3"), "/usr/bin/python3"]
    probe = 'import importlib.util,json,sys,pathlib; s=importlib.util.find_spec("torch"); print(json.dumps({"python":sys.executable,"package_root":str(pathlib.Path(s.origin).parent.parent) if s and s.origin else None}))'
    for executable in dict.fromkeys(filter(None, candidates)):
        process = subprocess.run([executable, "-c", probe], capture_output=True, text=True, timeout=10)
        if process.returncode == 0:
            data = json.loads(process.stdout)
            if data["package_root"]:
                return data["python"], [data["package_root"], *extra_paths]
    raise HarnessError("No existing PyTorch installation found; specify --torch-python and optional --torch-python-path. The example never downloads PyTorch.")


def prepare(root, upstream, isolation, torch_runtime=None):
    task = upstream["name"]
    project = root / "projects" / task
    cache = root / "downloads"
    cache.mkdir(parents=True, exist_ok=True)
    evaluation = root / "evaluation"
    evaluation.mkdir(parents=True, exist_ok=True)
    inputs, reference, baseline, candidate, metric, direction, hypothesis = fixtures(task)
    if not project.exists():
        project.mkdir(parents=True)
        for item in upstream["files"]:
            destination = project / item["destination"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(download(item, cache))
        if "wheel" in upstream:
            payload = download(upstream["wheel"], cache)
            with zipfile.ZipFile(io.BytesIO(payload)) as wheel:
                for entry in wheel.infolist():
                    destination = (project / "vendor" / entry.filename).resolve()
                    if project.resolve() not in destination.parents:
                        raise HarnessError("Wheel contains an escaping path")
                    if entry.is_dir():
                        destination.mkdir(parents=True, exist_ok=True)
                    else:
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(wheel.read(entry))
        adapter = task.replace("-", "_") + "_train.py"
        shutil.copyfile(EXAMPLES / "adapters" / adapter, project / "train.py")
        if task == "torch-lm":
            names = ["anna", "anne", "emma", "elle", "ella", "alan", "alina", "amelia", "liam", "lina", "mila", "nina", "noel", "nolan"]
            (project / "corpus.txt").write_text("\n".join(names * 4) + "\n")
        save(project / "settings.json", baseline)
        save(project / "upstream.json", upstream)
        core.git(project, "init", "-b", "main")
        core.git(project, "add", ".")
        core.git(project, "-c", "user.name=Harness Examples", "-c", "user.email=examples@example.invalid", "commit", "-m", "Pinned upstream and bounded adapter")
    if core.git(project, "status", "--porcelain").strip():
        raise HarnessError("Example project contains edits; preserving them: " + str(project))
    input_path, reference_path = evaluation / (task + "-inputs.jsonl"), evaluation / (task + "-reference.jsonl")
    jsonlines(input_path, inputs)
    jsonlines(reference_path, reference)
    contract = {
        "schema_version": 1, "hypothesis": hypothesis,
        "source": {"repository": str(project), "baseline": "HEAD", "allowed_paths": ["train.py", "settings.json"]},
        "training": {"argv": ["{python}", "train.py", "{inputs}", "{output}", "{seed}"], "inputs": str(input_path)},
        "evaluation": {"reference": str(reference_path), "metric": metric, "direction": direction},
        "execution": {"isolation": isolation, "timeout_seconds": 20, "max_artifact_bytes": 10485760},
        "acceptance": {"scope": "development", "seeds": [11, 22, 33, 44, 55], "confidence": .95, "minimum_effect": 0., "bootstrap_samples": 2000, "resampling_seed": 7},
    }
    if task == "torch-lm":
        executable, paths = torch_runtime
        contract["training"].update(
            argv=[executable, "train.py", "train", "{output}", "{seed}"],
            inference_argv=[executable, "train.py", "infer", "{inputs}", "{output}"], python_paths=paths,
        )
    path = root / (task + "-contract.json")
    save(path, contract)
    return path, candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".mih-demo")
    parser.add_argument("--task", choices=["all", "micrograd", "simplebayes", "torch-lm"], default="all")
    parser.add_argument("--torch-python", help="Use an existing interpreter with PyTorch; no PyTorch download")
    parser.add_argument("--torch-python-path", action="append", default=[], help="Explicit extra package directory for that interpreter")
    parser.add_argument("--isolation", choices=["auto", "macos-sandbox", "trusted-local"], default="auto")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    store = Store(root / "state")
    results = []
    for upstream in load(EXAMPLES / "upstreams.json"):
        task = upstream["name"]
        if args.task not in ("all", task):
            continue
        runtime = torch_environment(args.torch_python, args.torch_python_path) if task == "torch-lm" else None
        contract, candidate = prepare(root, upstream, args.isolation, runtime)
        if args.prepare_only:
            print(json.dumps({"task": task, "contract": str(contract), "candidate_settings": candidate}), flush=True)
            continue
        prepared = core.create(store, contract)
        experiment_id = prepared["id"]
        save(Path(prepared["workspace"]) / "settings.json", candidate)
        print(json.dumps({"task": task, "id": experiment_id, "status": "submitting"}), flush=True)
        core.submit(store, experiment_id)
        result = core.wait(store, experiment_id, timeout=60)
        save(root / (task + "-" + experiment_id + "-report.json"), result)
        compact = {
            "task": task, "id": experiment_id, "status": result["status"], "upstream": upstream["repository"],
            "upstream_commit": upstream["commit"], "isolation": result["isolation"],
            "acceptance": result.get("acceptance"), "error": result.get("error"),
            "wall_seconds": result.get("measurements", {}).get("total_wall_seconds"),
            "max_child_rss_mib": max((x["children_peak_rss_bytes_so_far"] / 2**20 for x in result.get("measurements", {}).get("attempts", [])), default=0),
            "evidence_dir": result["evidence_dir"],
        }
        results.append(compact)
        save(root / "summary.json", results)
        print(json.dumps(compact, ensure_ascii=False), flush=True)
    if any(r["status"] not in ("accepted", "rejected", "inconclusive") for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
