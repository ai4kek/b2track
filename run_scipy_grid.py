#!/usr/bin/env python3

import argparse
import csv
import itertools
import json
import os
import subprocess
import time
from multiprocessing import Pool
from pathlib import Path

from src.optimization_config import (
    METRICS_FIELDS,
    METRICS_PATH,
    PARAM_SPACE,
    PARAMS_PATH,
    TRACKING_CMD,
)

# Generate the grid of all parameter combinations
GRID = list(itertools.product(*[PARAM_SPACE[k] for k in PARAM_SPACE.keys()]))
NUM_GRID_POINTS = len(GRID)


def get_worker_metrics_path(worker_id):
    """Get the metrics file path for a specific worker."""
    if worker_id is None:  # Single worker mode
        return METRICS_PATH
    return Path(f"metrics_worker_{worker_id:02d}.csv")


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


def init_worker(worker_id):
    """Initialize worker-specific environment variables."""
    os.environ["WORKER_ID"] = str(worker_id)
    print(f"[INFO] Worker {worker_id} initialized")


# --- Setup CSV ---
def init_metrics_csv(worker_id=None):
    """Initialize metrics CSV file with header if it doesn't exist."""
    metrics_path = get_worker_metrics_path(worker_id)
    with metrics_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=METRICS_FIELDS)
        writer.writeheader()


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
        with worker_metrics.open("a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=METRICS_FIELDS)
            writer.writerow(row)

        return f1_score
    except Exception as e:
        print(f"[ERROR] Trial {trial_number}: Error processing metrics: {e}")
        return 0.0


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
def trial_objective(trial_number, param_values, worker_id=None):
    """Convert parameter values to dictionary, run tracking, and return F1 score."""
    # Convert parameter values to dictionary
    params = {}
    for i, param_name in enumerate(PARAM_SPACE.keys()):
        params[param_name] = param_values[i]

    # Run tracking and get F1 score
    f1_score = run_tracking_with_params(params, trial_number, worker_id)

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
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers",
    )
    parser.add_argument(
        "--slurm",
        action="store_true",
        default=False,
        help="Running as part of a Slurm job array",
    )
    args = parser.parse_args()

    # Get Slurm array job ID and total jobs if running on Slurm
    if args.slurm:
        job_id = int(os.environ.get("SLURM_ARRAY_TASK_ID", "0"))
        n_jobs = int(os.environ.get("SLURM_ARRAY_TASK_COUNT", "1"))
        print(f"[INFO] Running as Slurm job {job_id} of {n_jobs}")

        # Use job ID as worker ID
        os.environ["WORKER_ID"] = str(job_id)
        os.environ["NUM_WORKERS"] = str(n_jobs)

        # Each job handles its share of trials
        trials_per_job = args.max_trials // n_jobs
        start_trial = job_id * trials_per_job
        end_trial = (
            start_trial + trials_per_job if job_id < n_jobs - 1 else args.max_trials
        )
        grid_subset = GRID[start_trial:end_trial]

        print(f"[INFO] Job {job_id} handling trials {start_trial} to {end_trial-1}")

        # Initialize worker metrics file
        init_metrics_csv(job_id)

        # Run grid search for this worker's subset
        best_score = -1
        best_params = None

        for i, param_set in enumerate(grid_subset, start_trial + 1):
            print(f"[Trial {i}/{args.max_trials}]")
            score = trial_objective(i, param_set, job_id)

            if score > best_score:
                best_score = score
                best_params = param_set

    else:
        # Regular local execution
        if args.workers > 1:
            print(f"[INFO] Starting grid search with {args.workers} workers")

            # Initialize worker metrics files
            for worker_id in range(args.workers):
                init_metrics_csv(worker_id)

            # Divide grid points among workers
            grid_chunks = [GRID[i :: args.workers] for i in range(args.workers)]

            # Create pool and run grid search
            with Pool(processes=args.workers, initializer=init_worker) as pool:
                results = []
                for worker_id, chunk in enumerate(grid_chunks):
                    for i, param_set in enumerate(chunk, 1):
                        trial_num = (i - 1) * args.workers + worker_id + 1
                        results.append(
                            pool.apply_async(
                                trial_objective, (trial_num, param_set, worker_id)
                            )
                        )

                # Get all results
                scores = [r.get() for r in results]
                best_idx = max(range(len(scores)), key=scores.__getitem__)
                best_score = scores[best_idx]
                best_params = GRID[best_idx]

            # Merge worker metrics files
            merge_worker_metrics()

        else:
            # Single worker mode
            print("[INFO] Starting grid search with single worker")
            init_metrics_csv(None)

            best_score = -1
            best_params = None

            for i, param_set in enumerate(GRID[: args.max_trials], 1):
                print(f"[Trial {i}/{args.max_trials}]")
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
