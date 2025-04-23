#!/usr/bin/env python3

import argparse
import csv
import json
import os
import subprocess
import time
from multiprocessing import Lock
from pathlib import Path

from scipy.optimize import differential_evolution

from tracking_config import (
    MAX_TRIALS,
    METRICS_FIELDS,
    METRICS_PATH,
    PARAM_SPACE,
    PARAMS_PATH,
    RANDOM_SEED,
    TRACKING_CMD,
)

# Create a global lock for CSV file access
csv_lock = Lock()


# --- Setup CSV ---
def init_metrics_csv():
    """Initialize metrics CSV file with header if it doesn't exist."""
    with METRICS_PATH.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(METRICS_FIELDS)


# --- Update Metrics CSV ---
def update_metrics_csv(params, elapsed, trial_number):
    """Thread-safe function to update metrics CSV with parameters and execution time, returning F1 score."""
    try:
        with csv_lock:  # Thread-safe lock for parallel workers
            # Read current CSV content
            with METRICS_PATH.open("r", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            if not rows:
                print(f"[ERROR] Trial {trial_number}: No rows found in metrics.csv")
                return 0.0

            # Get F1 score from last row
            last_row = rows[-1]
            try:
                f1_score = float(last_row["f1_score"])
            except (ValueError, KeyError):
                print(f"[ERROR] Trial {trial_number}: Invalid f1_score in metrics.csv")
                f1_score = 0.0

            # Update execution time and parameters in the last row
            last_row["execution_time"] = f"{elapsed:.2f}"
            for key, value in params.items():
                last_row[key] = str(value)

            # Write updated content back to file
            with METRICS_PATH.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=METRICS_FIELDS)
                writer.writeheader()
                writer.writerows(rows)

        return f1_score
    except Exception as e:
        print(f"[ERROR] Trial {trial_number}: Error processing metrics: {e}")
        return 0.0


# --- Run Tracking ---
def run_tracking_with_params(params, trial_number):
    """Execute tracking pipeline with given parameters and return resulting F1 score."""
    # Write parameters to JSON
    with PARAMS_PATH.open("w") as f:
        json.dump(params, f, indent=2)

    # Run tracking command
    start = time.time()
    try:
        subprocess.run(TRACKING_CMD, check=True)
    except subprocess.CalledProcessError:
        print(f"[ERROR] Trial {trial_number}: basf2 execution failed.")
        return 0.0
    elapsed = round(time.time() - start, 2)
    print(f"Trial {trial_number} execution time: {elapsed:.1f}s")

    # Update metrics CSV and get F1 score
    return update_metrics_csv(params, elapsed, trial_number)


# --- Objective Function ---
def trial_objective(vector):
    """Convert parameter vector to values, run tracking, and return negative F1 score for minimization."""
    # Convert vector to parameter values
    params = {k: PARAM_SPACE[k][int(round(v))] for k, v in zip(PARAM_SPACE, vector)}

    # Get trial number
    if not hasattr(trial_objective, "counter"):
        trial_objective.counter = 0
    trial_objective.counter += 1
    trial_number = trial_objective.counter

    # Run tracking and get F1 score
    f1_score = run_tracking_with_params(params, trial_number)

    # Print trial info
    print(f"Trial {trial_number} | F1: {f1_score:.4f} | Params: {params}")

    # Return negative F1 score for minimization
    return -f1_score


# --- Main ---
def main():
    """Parse arguments, initialize CSV, run optimization, and save best parameters."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="SciPy Differential Evolution.")
    parser.add_argument(
        "--trials", type=int, default=MAX_TRIALS, help="Number of trials to run"
    )
    parser.add_argument(
        "--workers", type=int, default=os.cpu_count(), help="Number of parallel workers"
    )
    parser.add_argument(
        "--seed", type=int, default=RANDOM_SEED, help="Random seed for reproducibility"
    )
    args = parser.parse_args()

    # Initialize metrics CSV if needed
    if not METRICS_PATH.exists():
        init_metrics_csv()
        print(f"[INFO] Metrics CSV initialized: {METRICS_PATH}")

    # Set up optimization
    bounds = [(0, len(PARAM_SPACE[k]) - 1) for k in PARAM_SPACE]
    print(
        f"[INFO] Starting optimization with {args.workers} workers, {args.trials} trials, seed {args.seed}"
    )

    # Run differential evolution
    result = differential_evolution(
        trial_objective,
        bounds=bounds,
        strategy="best1bin",
        maxiter=args.trials,
        polish=False,
        disp=True,
        workers=args.workers,
        seed=args.seed,
        updating="deferred",
    )

    # Process results
    best_vector = result.x
    best_params = {
        k: PARAM_SPACE[k][int(round(v))] for k, v in zip(PARAM_SPACE, best_vector)
    }
    best_score = -result.fun

    # Print results
    print("\n[INFO] Optimization complete.")
    print("Best Parameters:")
    for k, v in best_params.items():
        print(f"  {k}: {v}")
    print(f"\n🏆 Best F1 Score: {best_score:.6f}\n")

    # Save best parameters
    with Path("best_params.json").open("w") as f:
        json.dump(best_params, f, indent=2)
    print("Best parameters saved to best_params.json\n")


# --- Entry Point ---
if __name__ == "__main__":
    main()
