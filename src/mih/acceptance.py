"""Exploratory paired bootstrap; not a confirmation or repeated-testing guarantee."""

import math
import random
import statistics

from .storage import HarnessError


def quantile(sorted_values, p):
    index = (len(sorted_values) - 1) * p
    lo = int(index)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (index - lo) * (sorted_values[hi] - sorted_values[lo])


def decide(baseline, candidate, policy, direction):
    required = policy["seeds"]
    note = "Exploratory finite-seed percentile bootstrap; no adaptive-selection or confirmation guarantee."
    if set(baseline) != set(required) or set(candidate) != set(required):
        return {"verdict": "inconclusive", "reason": "Missing required paired seeds", "scope": "development", "note": note}
    sign = 1 if direction == "maximize" else -1
    differences = [sign * (candidate[s] - baseline[s]) for s in required]
    if not all(math.isfinite(x) for x in differences):
        raise HarnessError("Non-finite paired measurement")
    if len(required) < 5:
        return {"verdict": "inconclusive", "reason": "At least five paired seeds required", "scope": "development", "note": note}
    rng = random.Random(policy.get("resampling_seed", 0))
    n = len(differences)
    samples = sorted(statistics.mean(rng.choices(differences, k=n)) for _ in range(policy["bootstrap_samples"]))
    tail = (1 - policy["confidence"]) / 2
    lower, upper = quantile(samples, tail), quantile(samples, 1 - tail)
    threshold = policy["minimum_effect"]
    verdict = "accepted" if lower > threshold else "rejected" if upper < threshold else "inconclusive"
    return {
        "verdict": verdict, "scope": "development", "method": "paired-percentile-bootstrap",
        "confidence": policy["confidence"], "minimum_effect": threshold,
        "paired_seeds": required, "differences": differences,
        "baseline_mean": statistics.mean(baseline.values()),
        "candidate_mean": statistics.mean(candidate.values()),
        "mean_improvement": statistics.mean(differences), "interval": [lower, upper],
        "bootstrap_samples": policy["bootstrap_samples"], "note": note,
    }
