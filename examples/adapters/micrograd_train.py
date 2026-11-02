"""Tiny real SGD training using pinned upstream micrograd; no numerical libraries."""

import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path("vendor").resolve()))
from micrograd.nn import MLP

inputs, output, seed = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
settings = json.loads(Path("settings.json").read_text())
random.seed(seed)
model = MLP(2, [4, 1])
data_rng = random.Random(1701)
training = [[data_rng.uniform(-1, 1), data_rng.uniform(-1, 1)] for _ in range(20)]
labels = [1 if x[0] + x[1] > 0 else -1 for x in training]
for step in range(settings["steps"]):
    losses = [(1 - y * model(x)).relu() for x, y in zip(training, labels)]
    loss = sum(losses) / len(losses)
    model.zero_grad()
    loss.backward()
    for parameter in model.parameters():
        parameter.data -= .12 * parameter.grad
    if step == settings["steps"] - 1:
        print(json.dumps({"step": step + 1, "training_loss": loss.data}))
(output / "model.json").write_text(json.dumps({"parameters": [p.data for p in model.parameters()], "architecture": [2, 4, 1]}))
with (output / "predictions.jsonl").open("w") as handle:
    for line in inputs.read_text().splitlines():
        row = json.loads(line)
        prediction = int(model(row["features"]).data > 0)
        handle.write(json.dumps({"id": row["id"], "prediction": prediction}) + "\n")
