"""CPU-only tiny GRU using the pinned PyTorch examples model.

Training and inference are separate commands; the harness scores predictions in
a third, trusted process. This script never receives reference labels.
"""

import json
from pathlib import Path
import sys

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path("vendor").resolve()))
from model import RNNModel

torch.set_num_threads(1)
torch.set_num_interop_threads(1)
torch.set_default_device("cpu")
mode = sys.argv[1]


def make_model(vocabulary):
    return RNNModel("GRU", len(vocabulary), 8, 8, 1, dropout=0).cpu()


if mode == "train":
    output, seed = Path(sys.argv[2]), int(sys.argv[3])
    torch.manual_seed(seed)
    settings = json.loads(Path("settings.json").read_text())
    names = Path("corpus.txt").read_text().splitlines()
    vocabulary = sorted(set("".join(names)) | {"^"})
    ids = {char: i for i, char in enumerate(vocabulary)}
    length = max(len(name) for name in names) + 1
    x = torch.full((length, len(names)), ids["^"], dtype=torch.long)
    y = torch.full((length, len(names)), -100, dtype=torch.long)
    for column, name in enumerate(names):
        sequence = [ids["^"]] + [ids[char] for char in name] + [ids["^"]]
        x[:len(sequence) - 1, column] = torch.tensor(sequence[:-1])
        y[:len(sequence) - 1, column] = torch.tensor(sequence[1:])
    model = make_model(vocabulary)
    optimizer = torch.optim.AdamW(model.parameters(), lr=.03)
    model.train()
    for step in range(settings["steps"]):
        optimizer.zero_grad()
        logits, _ = model(x, model.init_hidden(len(names)))
        loss = F.nll_loss(logits, y.reshape(-1), ignore_index=-100)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
        optimizer.step()
    torch.save({"state_dict": model.state_dict(), "vocabulary": vocabulary}, output / "checkpoint.pt")
    (output / "model.json").write_text(json.dumps({"parameters": sum(p.numel() for p in model.parameters()), "steps": settings["steps"], "torch": torch.__version__, "device": "cpu", "threads": 1}))
    print(json.dumps({"training_loss": loss.item(), "steps": settings["steps"]}))
elif mode == "infer":
    inputs, output = Path(sys.argv[2]), Path(sys.argv[3])
    checkpoint = torch.load(output / "checkpoint.pt", map_location="cpu", weights_only=True)
    vocabulary = checkpoint["vocabulary"]
    ids = {char: i for i, char in enumerate(vocabulary)}
    model = make_model(vocabulary)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    with torch.no_grad(), (output / "predictions.jsonl").open("w") as handle:
        for line in inputs.read_text().splitlines():
            row = json.loads(line)
            sequence = torch.tensor([ids[c] for c in "^" + row["context"]], dtype=torch.long).unsqueeze(1)
            logits, _ = model(sequence, model.init_hidden(1))
            probabilities = logits[-1].exp().tolist()
            handle.write(json.dumps({"id": row["id"], "probabilities": dict(zip(vocabulary, probabilities))}) + "\n")
else:
    raise ValueError("Expected train or infer")
