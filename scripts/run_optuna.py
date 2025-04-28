#!/usr/bin/env python3

import argparse
import csv
import json
import os
import subprocess
import time
from pathlib import Path

import optuna
from optuna.samplers import TPESampler
from optuna.storages import RDBStorage

from src.optimization_config import (
    MAX_TRIALS,
    METRICS_FIELDS,
    METRICS_PATH,
    PARAM_SPACE,
    PARAMS_PATH,
    RANDOM_SEED,
    TRACKING_CMD,
)

# --- Configuration ---
SQLITE_PATH = "sqlite:///optuna_study.db"
STUDY_NAME = "tracking_optimization"


# --- Worker Management ---
def get_worker_metrics_path(worker_id=None):
    """Get path to worker-specific metrics file."""
    if worker_id is None:
        return METRICS_PATH
    return Path(f"metrics_worker_{worker_id:02d}.csv")


def init_metrics_csv(worker_id=None):
    """Initialize metrics CSV file with header if it doesn't exist."""
    metrics_path = get_worker_metrics_path(worker_id)
    with metrics_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=METRICS_FIELDS)
        writer.writeheader()


def merge_worker_metrics():
    """Merge all worker metrics files into the final metrics.csv."""
    all_rows = []
    worker_files = sorted(Path().glob("metrics_worker_*.csv"))

    # Read all worker files
    for worker_file in worker_files:
        with worker_file.open("r", newline="") as f:
            reader = csv.DictReader(f)
            all_rows.extend(list(reader))
        worker_file.unlink()  # Clean up worker file

    # Write merged results
    if all_rows:
        with METRICS_PATH.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=METRICS_FIELDS)
            writer.writeheader()
            writer.writerows(all_rows)


# --- Update Metrics CSV ---
def update_metrics_csv(params, elapsed, trial_number, worker_id=None):
    """Thread-safe function to update metrics CSV with parameters and execution time, returning F1 score."""
    try:
        trial_metrics = f"metrics_trial_{trial_number:03d}.csv"
        trial_metrics_path = Path(trial_metrics)

        # Read trial metrics file
        with trial_metrics_path.open("r", newline="") as f:
            reader = csv.DictReader(f)
            row = list(reader)[-1]
            f1_score = float(row["f1_score"])

        # Update execution time and parameters
        row["execution_time"] = f"{elapsed:.2f}"
        for key, value in params.items():
            row[key] = str(value)

        # Append to worker-specific metrics file
        worker_metrics = get_worker_metrics_path(worker_id)
        is_first_trial = not worker_metrics.exists()
        with worker_metrics.open("a" if not is_first_trial else "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=METRICS_FIELDS)
            if is_first_trial:
                writer.writeheader()
            writer.writerow(row)

        return f1_score
    except Exception as e:
        print(f"[ERROR] Trial {trial_number}: Error processing metrics: {e}")
        return 0.0
    finally:
        # Clean up trial metrics file
        trial_metrics_path.unlink(missing_ok=True)


# --- Run Tracking ---
def run_tracking_with_params(params, trial_number, worker_id=None):
    """Execute tracking pipeline with given parameters and return resulting F1 score."""
    # Write parameters to JSON
    with PARAMS_PATH.open("w") as f:
        json.dump(params, f, indent=2)

    # Run tracking with trial-specific metrics file
    trial_metrics = f"metrics_trial_{trial_number:03d}.csv"
    start = time.time()
    try:
        cmd = TRACKING_CMD + ["--metrics", trial_metrics]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print(f"[ERROR] Trial {trial_number}: basf2 execution failed.")
        return 0.0
    elapsed = round(time.time() - start, 2)
    print(f"Trial {trial_number} execution time: {elapsed:.1f}s")

    # Update metrics CSV and get F1 score
    return update_metrics_csv(params, elapsed, trial_number, worker_id)


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
    parser.add_argument("--slurm", action="store_true", help="Run in Slurm mode")
    args = parser.parse_args()

    # Handle Slurm array job
    if args.slurm:
        # Get Slurm array job ID and total jobs
        job_id = int(os.environ.get("SLURM_ARRAY_TASK_ID", 0))
        n_jobs = int(os.environ.get("SLURM_ARRAY_TASK_COUNT", 1))

        # Calculate trials for this job
        trials_per_job = args.trials // n_jobs
        start_trial = job_id * trials_per_job
        end_trial = start_trial + trials_per_job if job_id < n_jobs - 1 else args.trials

        print(f"[INFO] Job {job_id} handling trials {start_trial} to {end_trial-1}")

        # Initialize worker metrics
        init_metrics_csv(job_id)

        # Create Optuna study for this job
        storage = RDBStorage(url=SQLITE_PATH)
        sampler = TPESampler(seed=args.seed + job_id)  # Different seed per job
        study = optuna.create_study(
            direction="maximize",
            study_name=f"{STUDY_NAME}_job_{job_id}",
            storage=storage,
            sampler=sampler,
            load_if_exists=True,
        )

        # Run optimization for this job's trials
        study.optimize(
            lambda trial: trial_objective(trial, job_id),
            n_trials=end_trial - start_trial,
            n_jobs=1,  # Single worker per Slurm job
        )

    else:
        # Regular local execution
        os.environ["NUM_WORKERS"] = str(args.workers)
        print(
            f"[INFO] Starting optimization with {args.workers} workers, {args.trials} trials, seed {args.seed}"
        )

        # Initialize worker metrics if using multiple workers
        if args.workers > 1:
            for i in range(args.workers):
                init_metrics_csv(i)
        else:
            init_metrics_csv()

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
        study.optimize(
            lambda trial: trial_objective(
                trial, trial.number % args.workers if args.workers > 1 else None
            ),
            n_trials=args.trials,
            n_jobs=args.workers,
        )

        # Merge worker metrics files if using multiple workers
        if args.workers > 1:
            print("\n[INFO] Merging worker metrics files...")
            merge_worker_metrics()

    print("\n[INFO] Optimization complete.")
    print("Best Parameters:")
    for k, v in study.best_params.items():
        print(f"  {k}: {v}")
    print(f"\n🏆 Best F1 Score: {study.best_value:.4f}")
    print(f"\nTo view results in dashboard, run: optuna-dashboard {SQLITE_PATH}\n")


# --- Entry Point ---
if __name__ == "__main__":
    main()
