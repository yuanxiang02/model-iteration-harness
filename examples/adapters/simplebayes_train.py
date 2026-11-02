"""Tiny text classification with the upstream SimpleBayes library."""

import json
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path("vendor").resolve()))
from simplebayes import SimpleBayes

inputs, output, seed = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
settings = json.loads(Path("settings.json").read_text())


def tokenize(text):
    words = text.lower().split()
    if settings["bigrams"]:
        return words + ["_".join(pair) for pair in zip(words, words[1:])]
    return words


training = [
    ("positive", "good movie"), ("positive", "great film"),
    ("positive", "not bad movie"), ("positive", "not terrible film"),
    ("negative", "bad film"), ("negative", "terrible movie"),
    ("negative", "not good film"), ("negative", "not great movie"),
]
random.Random(seed).shuffle(training)
model = SimpleBayes(tokenizer=tokenize, alpha=1.0)
for label, text in training:
    model.train(label, text)
model.save_to_file(str((output / "model.json").resolve()))
with (output / "predictions.jsonl").open("w") as handle:
    for line in inputs.read_text().splitlines():
        row = json.loads(line)
        prediction = model.classify_result(row["text"]).category
        handle.write(json.dumps({"id": row["id"], "prediction": prediction}) + "\n")
print(json.dumps({"training_documents": len(training), "bigrams": settings["bigrams"]}))
