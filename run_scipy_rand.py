"""
SciPy Optimization Script for Belle II Tracking Parameters

This script uses SciPy's `differential_evolution` to search for a combination of tracking
parameters that maximize the F1 score — the harmonic mean of tracking efficiency and purity.

How It Works:
-------------
- The search space is discretized and flattened for compatibility with SciPy.
- Each parameter set is converted to a JSON file (`params.json`).
- `basf2 run_tracking_svd.py` is invoked to run the tracking algorithm.
- The output `metrics.csv` is parsed to extract efficiency and purity.
- The F1 score is computed and returned as the objective.
- The objective is negated since `differential_evolution` minimizes the objective.

Usage:
------
    python run_scipy.py

Dependencies:
-------------
- Belle II software stack (basf2)
- SciPy (comes pre-installed in many Python distributions)
- `run_tracking_svd.py` and `TrackingMetrics` must handle `params.json` and write `metrics.csv`.

Author:
-------
ChatGPT
"""

import json
import subprocess
import time
import csv
from pathlib import Path
import numpy as np
from scipy.optimize import differential_evolution

# --- Define the discrete search space ---

PARAM_SPACE = {
    "maximalDeltaPhi": [0.2, 0.3, 0.4],
    "maximalLayerJump": [2, 4, 6],
    "minimalPtRequirement": [0.0, 0.1],
    "pathMaximalCandidatesInFlight": [2, 3],
    "stateMaximalHitCandidates": [3, 4],
}

PARAM_KEYS = list(PARAM_SPACE.keys())
PARAM_CHOICES = [PARAM_SPACE[key] for key in PARAM_KEYS]
BOUNDS = [(0, len(choices) - 1) for choices in PARAM_CHOICES]

METRICS_FILE = Path("metrics.csv")


# --- Helper to convert float vector to parameter dict ---
def vector_to_params(vector):
    return {
        key: PARAM_SPACE[key][int(round(val))] for key, val in zip(PARAM_KEYS, vector)
    }


# --- Objective function (to be minimized, so return -F1) ---
def objective(vector):
    params = vector_to_params(vector)

    with open("params.json", "w") as f:
        json.dump(params, f, indent=2)

    start = time.time()
    try:
        subprocess.run(["basf2", "run_tracking_svd.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Run failed: {e}")
        return 1.0  # Penalize failed runs

    elapsed = time.time() - start

    if not METRICS_FILE.exists():
        print("[ERROR] metrics.csv not found.")
        return 1.0

    with METRICS_FILE.open(newline="") as f:
        rows = list(csv.DictReader(f))
        if not rows:
            print("[ERROR] No data in metrics.csv")
            return 1.0

        last_row = rows[-1]
        eff = float(last_row["efficiency"])
        pur = float(last_row["purity"])

        f1 = 2 * eff * pur / (eff + pur + 1e-8)
        print(
            f"[INFO] F1 = {f1:.4f} (eff={eff:.3f}, pur={pur:.3f})  Time: {elapsed:.1f}s"
        )

        return -f1  # Negate because we are minimizing


# --- Run optimization ---
if __name__ == "__main__":
    result = differential_evolution(
        objective,
        bounds=BOUNDS,
        strategy="best1bin",
        maxiter=10,
        polish=False,
        disp=True,
        workers=1,  # Can set to -1 to use all CPUs (needs `multiprocessing` safe code)
    )

    best_params = vector_to_params(result.x)
    best_score = -result.fun

    print("\n✅ Best Parameters Found:")
    for k, v in best_params.items():
        print(f"  {k}: {v}")
    print(f"\n🔎 Best F1 Score: {best_score:.4f}")
