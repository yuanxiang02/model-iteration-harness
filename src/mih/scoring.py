"""Standalone trusted scoring. This file is copied into each frozen experiment."""

import argparse
import json
import math
from pathlib import Path


def records(path):
    data = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            key = row["id"]
            if not isinstance(key, str) or not key or key in data:
                raise ValueError("Invalid or duplicate example ID")
            data[key] = row
    if not data:
        raise ValueError("Empty predictions/reference")
    return data


def score(predictions, reference, metric):
    pred, gold = records(predictions), records(reference)
    if pred.keys() != gold.keys():
        raise ValueError("Prediction coverage must exactly match reference IDs")
    values = []
    for key, expected in gold.items():
        output = pred[key]
        if metric == "accuracy":
            value = output["prediction"]
            if not isinstance(value, (str, bool, int, float)) or isinstance(value, float) and not math.isfinite(value):
                raise ValueError("Invalid prediction")
            values.append(float(value == expected["target"]))
        elif metric == "nll":
            probabilities = output["probabilities"]
            if not isinstance(probabilities, dict) or not probabilities:
                raise ValueError("Expected probability distribution")
            numbers = list(probabilities.values())
            if not all(type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1 for x in numbers):
                raise ValueError("Invalid probability")
            if abs(sum(numbers) - 1) > 1e-6:
                raise ValueError("Probabilities must sum to one")
            probability = probabilities.get(str(expected["target"]), 0.0)
            if probability <= 0:
                raise ValueError("Reference target has zero probability")
            values.append(-math.log(probability))
        else:
            raise ValueError("Unknown metric")
    return {"metric": metric, "value": sum(values) / len(values), "count": len(values)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--metric", choices=["accuracy", "nll"], required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = score(args.predictions, args.reference, args.metric)
    Path(args.output).write_text(json.dumps(result, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
