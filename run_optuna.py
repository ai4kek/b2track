#!/usr/bin/env python3

import argparse
import csv
import json
import os
import subprocess
import time
from multiprocessing import Lock

import optuna
from optuna.samplers import TPESampler
from optuna.storages import RDBStorage

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

# --- Configuration ---
SQLITE_PATH = "sqlite:///optuna_study.db"
STUDY_NAME = "tracking_optimization"


# --- Setup CSV ---
def init_metrics_csv():
    """Initialize metrics CSV file with header if it doesn't exist."""
    with METRICS_PATH.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(METRICS_FIELDS)


# --- Update Metrics CSV ---
def update_metrics_csv(params, elapsed, trial_number):
    """Update the metrics CSV with parameters and execution time.
    Thread-safe function that uses a lock to prevent race conditions."""
    try:
        # Acquire the lock before accessing the CSV file
        with csv_lock:
            # Read the current CSV content
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

            # Write the updated content back to the file
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
def trial_objective(trial):
    """Sample parameters using Optuna, run tracking, and return F1 score for maximization."""
    # Sample parameters for the trial
    params = {k: trial.suggest_categorical(k, v) for k, v in PARAM_SPACE.items()}
    trial_number = trial.number

    # Run tracking and get F1 score
    f1_score = run_tracking_with_params(params, trial_number)

    # Print trial info
    print(f"Trial {trial_number} | F1: {f1_score:.4f} | Params: {params}")

    return f1_score


# --- Main ---
def main():
    """Parse arguments, initialize CSV, run Optuna optimization, and report best parameters."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Optuna Optimization.")
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

    print(
        f"[INFO] Starting optimization with {args.workers} workers, {args.trials} trials, seed {args.seed}"
    )

    # Create Optuna study
    storage = RDBStorage(url=SQLITE_PATH)
    sampler = TPESampler(seed=args.seed)
    study = optuna.create_study(
        direction="maximize",
        study_name=STUDY_NAME,
        storage=storage,
        sampler=sampler,
        load_if_exists=True,
    )

    # Run optimization
    study.optimize(trial_objective, n_trials=args.trials, n_jobs=args.workers)

    print("\n[INFO] Optimization complete.")
    print("Best Parameters:")
    for k, v in study.best_params.items():
        print(f"  {k}: {v}")
    print(f"\n🏆 Best F1 Score: {study.best_value:.4f}")
    print(f"\nTo view results in dashboard, run: optuna-dashboard {SQLITE_PATH}\n")


# --- Entry Point ---
if __name__ == "__main__":
    main()
