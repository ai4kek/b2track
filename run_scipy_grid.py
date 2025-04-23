#!/usr/bin/env python3

import argparse
import csv
import itertools
import json
import subprocess
import time
from multiprocessing import Lock
from pathlib import Path

from tracking_config import (
    METRICS_FIELDS,
    METRICS_PATH,
    PARAM_SPACE,
    PARAMS_PATH,
    TRACKING_CMD,
)

# Create a global lock for CSV file access
csv_lock = Lock()

# Generate the grid of all parameter combinations
GRID = list(itertools.product(*[PARAM_SPACE[k] for k in PARAM_SPACE.keys()]))
NUM_GRID_POINTS = len(GRID)


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
def trial_objective(trial_number, param_values):
    """Convert parameter values to dictionary, run tracking, and return F1 score."""
    # Convert parameter values to dictionary
    params = {}
    for i, param_name in enumerate(PARAM_SPACE.keys()):
        params[param_name] = param_values[i]

    # Run tracking and get F1 score
    f1_score = run_tracking_with_params(params, trial_number)

    # Print trial info
    print(f"Trial {trial_number} | F1: {f1_score:.4f} | Params: {params}")

    return f1_score


# --- Main ---
def main():
    """Parse arguments, initialize CSV, run grid search, and report best parameters."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Grid Search Optimization.")
    parser.add_argument(
        "--max-trials",
        type=int,
        default=NUM_GRID_POINTS,
        help="Maximum number of trials to run (will use first N points from grid)",
    )
    args = parser.parse_args()

    # Initialize metrics CSV if needed
    if not METRICS_PATH.exists():
        init_metrics_csv()
        print(f"[INFO] Metrics CSV initialized: {METRICS_PATH}")

    # Limit trials if requested
    num_trials = min(args.max_trials, NUM_GRID_POINTS)
    grid_subset = GRID[:num_trials]

    print(
        f"[INFO] Starting grid search with {num_trials} trials out of {NUM_GRID_POINTS} possible combinations"
    )

    # Run grid search
    best_score = -1
    best_params = None

    for i, param_set in enumerate(grid_subset, 1):
        print(f"[Trial {i}/{num_trials}]")
        score = trial_objective(i, param_set)

        if score > best_score:
            best_score = score
            best_params = param_set

    # Print results
    print("\n[INFO] Grid search complete.")
    if best_params:
        print("Best Parameters:")
        for i, (param_name, value) in enumerate(zip(PARAM_SPACE.keys(), best_params)):
            print(f"  {param_name}: {value}")
        print(f"\n🏆 Best F1 Score: {best_score:.4f}\n")

        # Save best parameters
        best_params_dict = dict(zip(PARAM_SPACE.keys(), best_params))
        with Path("best_params.json").open("w") as f:
            json.dump(best_params_dict, f, indent=2)
        print("Best parameters saved to best_params.json\n")


# --- Entry Point ---
if __name__ == "__main__":
    main()
