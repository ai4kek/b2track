"""
Grid Search for Belle II Tracking Parameters

Performs exhaustive search over defined parameter combinations. 
Runs tracking script for each set and saves results to metrics.csv.

Output Columns:
---------------
trial, maximalDeltaPhi, maximalLayerJump, ..., efficiency, purity, f1_score, execution_time

Usage:
-------
    python run_gridsearch.py

Author:
-------
ChatGPT (updated for metrics.csv style)
"""

import itertools
import subprocess
import time
import json
import csv
from pathlib import Path

# Define discrete parameter grid
PARAM_SPACE = {
    "maximalDeltaPhi": [0.2, 0.3, 0.4],
    "maximalLayerJump": [2, 4, 6],
    "minimalPtRequirement": [0.0, 0.1],
    "pathMaximalCandidatesInFlight": [2, 3],
    "stateMaximalHitCandidates": [3, 4],
}

PARAM_KEYS = list(PARAM_SPACE.keys())
GRID = list(itertools.product(*[PARAM_SPACE[k] for k in PARAM_KEYS]))
NUM_TRIALS = len(GRID)

# Output file: same as original usage
metrics_path = Path("metrics.csv")

# Prepare metrics file if it doesn't exist
if not metrics_path.exists():
    with metrics_path.open("w", newline="") as f:
        writer = csv.writer(f)
        header = (
            ["trial"]
            + PARAM_KEYS
            + ["efficiency", "purity", "f1_score", "execution_time"]
        )
        writer.writerow(header)


def run_trial(trial_id, param_values):
    # Prepare dict for basf2
    params = dict(zip(PARAM_KEYS, param_values))
    with open("params.json", "w") as f:
        json.dump(params, f, indent=2)

    # Run Belle II tracking
    start = time.time()
    try:
        subprocess.run(["basf2", "run_tracking_svd.py"], check=True)
    except subprocess.CalledProcessError:
        print(f"[ERROR] Failed basf2 run for trial {trial_id}")
        return None
    elapsed = round(time.time() - start, 2)

    # Read metrics from the metrics file
    with metrics_path.open(newline="") as f:
        rows = list(csv.DictReader(f))
        if not rows:
            print("[ERROR] metrics.csv is empty after run.")
            return None

        last = rows[-1]
        try:
            eff = float(last["efficiency"])
            pur = float(last["purity"])
        except (KeyError, ValueError):
            print("[ERROR] Could not parse efficiency/purity.")
            return None

        f1 = 2 * eff * pur / (eff + pur + 1e-8)

    # Append row to metrics.csv
    with metrics_path.open("a", newline="") as f:
        writer = csv.writer(f)
        row = [trial_id] + list(param_values) + [eff, pur, f1, elapsed]
        writer.writerow(row)

    return f1


# --- Run Grid Search ---
best_score = -1
best_params = None

print(f"🔍 Starting grid search over {NUM_TRIALS} trials...")

for i, param_set in enumerate(GRID, 1):
    print(f"[Trial {i}/{NUM_TRIALS}] Params: {dict(zip(PARAM_KEYS, param_set))}")
    score = run_trial(i, param_set)
    if score is not None and score > best_score:
        best_score = score
        best_params = param_set

# --- Final Result ---
print("\n✅ Grid search complete.")
if best_params:
    print(f"\n🏆 Best F1 Score: {best_score:.4f}")
    print("🧮 Best Parameters:")
    for k, v in zip(PARAM_KEYS, best_params):
        print(f"  {k}: {v}")
