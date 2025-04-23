#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

import csv
import json
import random
import subprocess
import time
from pathlib import Path

# Number of trials
NUM_TRIALS = 10

# Parameter search space
SEARCH_SPACE = {
    "maximalDeltaPhi": [0.2, 0.3, 0.4],
    "maximalLayerJump": [2, 4, 6],
    "minimalPtRequirement": [0.0, 0.1],
    "pathMaximalCandidatesInFlight": [2, 3],
    "stateMaximalHitCandidates": [3, 4],
}


def get_random_params(space):
    return {k: random.choice(v) for k, v in space.items()}


# Results CSV path
results_path = Path("metrics.csv")

# Write CSV header if it doesn't exist
if not results_path.exists():
    with results_path.open(mode="w", newline="") as f:
        writer = csv.writer(f)
        header = list(SEARCH_SPACE.keys()) + [
            "efficiency",
            "purity",
            "finalstate",
            "execution_time",
        ]
        writer.writerow(header)

# Run trials
for trial in range(NUM_TRIALS):
    print(f"\nTrial {trial + 1}/{NUM_TRIALS}")

    # Randomly sample params
    params = get_random_params(SEARCH_SPACE)

    # Save to JSON
    with open("params.json", "w") as f:
        json.dump(params, f, indent=2)

    # Run tracking script and time it
    start_time = time.time()
    subprocess.run(["basf2", "run_tracking_svd.py"])
    elapsed_time = time.time() - start_time

    print(f"[INFO] Execution time: {elapsed_time:.2f} seconds")

    # Read and update last row in CSV
    with results_path.open(newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print(f"[ERROR] No rows found in {results_path}")
        continue

    rows[-1]["execution_time"] = round(elapsed_time, 2)

    # Write back with updated execution time
    with results_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
