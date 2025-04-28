#!/usr/bin/env python3

import argparse
import csv
import json
import os
import subprocess
import time
from pathlib import Path

from scipy.optimize import differential_evolution

from src.optimization_config import (
    MAX_TRIALS,
    METRICS_FIELDS,
    METRICS_PATH,
    PARAM_SPACE,
    PARAMS_PATH,
    RANDOM_SEED,
    TRACKING_CMD,
)


def init_worker(worker_id):
    """Initialize worker-specific environment variables."""
    os.environ["WORKER_ID"] = str(worker_id)
    print(f"[INFO] Worker {worker_id} initialized")


def get_worker_metrics_path(worker_id):
    """Get the metrics file path for a specific worker."""
    if worker_id is None:  # Single worker mode
        return METRICS_PATH
    return Path(f"metrics_worker_{worker_id:02d}.csv")


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


def run_tracking_with_params(params, trial_number, worker_id=None):
    """Execute tracking pipeline with given parameters and return resulting F1 score."""
    # Write parameters to JSON for tracking script
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


def trial_objective(vector):
    """Run a trial with given parameters and return negative F1 score for minimization."""
    # Convert vector to parameter values
    params = {k: PARAM_SPACE[k][int(round(v))] for k, v in zip(PARAM_SPACE, vector)}

    # Get trial number and worker ID
    if not hasattr(trial_objective, "counter"):
        trial_objective.counter = 0
        trial_objective.worker_id = int(os.environ.get("WORKER_ID", "0"))
    trial_objective.counter += 1

    # Run tracking and get F1 score
    f1_score = run_tracking_with_params(
        params,
        trial_objective.counter,
        worker_id=(
            trial_objective.worker_id
            if int(os.environ.get("NUM_WORKERS", "1")) > 1
            else None
        ),
    )
    print(
        f"Worker {trial_objective.worker_id} | Trial {trial_objective.counter} | F1: {f1_score:.4f} | Params: {params}"
    )

    return -f1_score


def main():
    """Run optimization to find best tracking parameters."""
    parser = argparse.ArgumentParser(
        description="Optimize tracking parameters using SciPy Differential Evolution."
    )
    parser.add_argument(
        "--trials", type=int, default=MAX_TRIALS, help="Number of trials to run"
    )
    parser.add_argument(
        "--workers", type=int, default=os.cpu_count(), help="Number of parallel workers"
    )
    parser.add_argument(
        "--seed", type=int, default=RANDOM_SEED, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--slurm",
        action="store_true",
        default=False,
        help="Running as part of a Slurm job array",
    )
    args = parser.parse_args()

    # Setup optimization bounds
    bounds = [(0, len(PARAM_SPACE[k]) - 1) for k in PARAM_SPACE]

    # Get Slurm array job ID and total jobs if running on Slurm
    if args.slurm:
        job_id = int(os.environ.get("SLURM_ARRAY_TASK_ID", "0"))
        n_jobs = int(os.environ.get("SLURM_ARRAY_TASK_COUNT", "1"))
        print(f"[INFO] Running as Slurm job {job_id} of {n_jobs}")

        # Use job ID as worker ID
        os.environ["WORKER_ID"] = str(job_id)
        os.environ["NUM_WORKERS"] = str(n_jobs)

        # Each job handles its share of trials
        trials_per_job = args.trials // n_jobs
        start_trial = job_id * trials_per_job
        end_trial = start_trial + trials_per_job if job_id < n_jobs - 1 else args.trials

        print(f"[INFO] Job {job_id} handling trials {start_trial} to {end_trial-1}")

        # Run optimization with single worker (each Slurm job is its own worker)
        result = differential_evolution(
            trial_objective,
            bounds=bounds,
            strategy="best1bin",
            maxiter=end_trial - start_trial,
            polish=False,
            disp=True,
            workers=1,
            seed=args.seed + job_id,  # Different seed per job
            updating="deferred",
        )

    else:
        # Regular local execution
        os.environ["NUM_WORKERS"] = str(args.workers)
        print(
            f"[INFO] optimization file with {args.workers} workers, {args.trials} trials, seed {args.seed}"
        )

        if args.workers > 1:
            from multiprocessing.pool import Pool

            with Pool(
                processes=args.workers, initializer=init_worker, initargs=(0,)
            ) as pool:
                result = differential_evolution(
                    trial_objective,
                    bounds=bounds,
                    strategy="best1bin",
                    maxiter=args.trials,
                    polish=False,
                    disp=True,
                    workers=pool.map,
                    seed=args.seed,
                    updating="deferred",
                )
        else:
            result = differential_evolution(
                trial_objective,
                bounds=bounds,
                strategy="best1bin",
                maxiter=args.trials,
                polish=False,
                disp=True,
                workers=1,
                seed=args.seed,
                updating="deferred",
            )

    # Merge worker metrics files if using multiple workers
    if args.workers > 1:
        print("\n[INFO] Merging worker metrics files...")
        merge_worker_metrics()

    # Save best parameters
    best_params = {
        k: PARAM_SPACE[k][int(round(v))] for k, v in zip(PARAM_SPACE, result.x)
    }
    print("\n[INFO] Optimization complete.")
    print("Best Parameters:")
    for k, v in best_params.items():
        print(f"  {k}: {v}")
    print(f"\n🏆 Best F1 Score: {-result.fun:.6f}\n")

    with Path("best_params.json").open("w") as f:
        json.dump(best_params, f, indent=2)
    print("Best parameters saved to best_params.json\n")


if __name__ == "__main__":
    main()
