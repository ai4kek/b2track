#!/usr/bin/env python3

import argparse
import csv
import hashlib
import itertools
import json
import logging
import multiprocessing
import os
import subprocess
import sys
import time
from multiprocessing import Pool
from pathlib import Path
from src.optimization_config import (
    METRICS_FIELDS,
    PARAM_SPACE,
    TRACKING_CMD,
)

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "grid_optimization.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(processName)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("grid_optimizer")

# Initialize global variables for worker tracking
_worker_id = 0
_trial_counter = 0

# Generate the grid of all parameter combinations
GRID = list(itertools.product(*[PARAM_SPACE[k] for k in PARAM_SPACE.keys()]))
NUM_GRID_POINTS = len(GRID)


def init_worker(worker_ids):
    """Initialize worker-specific environment variables and counter."""
    global _worker_id, _trial_counter
    # Each process gets a worker ID based on its process ID
    process_idx = multiprocessing.current_process()._identity[0] - 1
    if process_idx < 0:  # Main process
        _worker_id = 0
    else:
        _worker_id = worker_ids[process_idx % len(worker_ids)]
    _trial_counter = 0
    os.environ["WORKER_ID"] = str(_worker_id)
    logger.info(f"Worker {_worker_id} initialized (PID: {os.getpid()})")


def compute_param_hash(params):
    """Hash the sorted JSON string of params for uniqueness."""
    param_str = json.dumps(params, sort_keys=True)
    return hashlib.sha1(param_str.encode()).hexdigest()[:10]


def cleanup_worker_files():
    """Clean up worker-specific parameter files."""
    for param_file in Path().glob("params_worker_*.json"):
        param_file.unlink(missing_ok=True)


def get_worker_params_path(worker_id):
    """Get the worker-specific parameters file path."""
    if worker_id is None:
        raise ValueError("Worker ID must be provided")
    return Path(f"params_worker_{worker_id:02d}.json")


def get_worker_metrics_path(worker_id):
    """Get the worker-specific metrics file path."""
    if worker_id is None:
        raise ValueError("Worker ID must be provided")
    return Path(f"metrics_worker_{worker_id:02d}.csv")


# --- Handle Metrics CSV ---
def update_metrics_csv(params, elapsed, trial_number, worker_id, param_hash=None):
    """Update worker-specific metrics CSV with trial results and return F1 score."""
    if worker_id is None:
        raise ValueError("Worker ID must be provided for thread-safe operation")
    try:
        # Read trial results
        trial_metrics = get_worker_metrics_path(worker_id)
        with trial_metrics.open("r", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            row = rows[-1] if rows else {}
            f1_score = float(row.get("f1_score", 0.0))
        # Update row with additional info
        row.update(
            {
                "execution_time": f"{elapsed:.2f}",
                "worker_id": str(worker_id),
                "param_hash": param_hash if param_hash else "",
                **{k: str(v) for k, v in params.items()},
            }
        )
        # Append to worker-specific metrics file
        is_new_file = not trial_metrics.exists()
        with trial_metrics.open("a" if not is_new_file else "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=METRICS_FIELDS)
            if is_new_file:
                writer.writeheader()
            writer.writerow(row)
        return f1_score
    except Exception as e:
        print(f"[ERROR] Trial {trial_number}: Error processing metrics: {e}")
        return 0.0


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
        with open("metrics.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=METRICS_FIELDS)
            writer.writeheader()
            writer.writerows(all_rows)


# --- Run Tracking ---
def run_tracking_with_params(params, trial_number, worker_id, param_hash=None):
    """Execute tracking pipeline and return resulting F1 score."""
    if worker_id is None:
        raise ValueError("Worker ID must be provided for thread-safe operation")
    if param_hash is None:
        param_hash = compute_param_hash(params)
    print(
        f"[START] Worker {worker_id} | Trial {trial_number} | param_hash: {param_hash} | Params: {params}"
    )
    # Save parameters to worker-specific JSON file
    params_path = get_worker_params_path(worker_id)
    with params_path.open("w") as f:
        json.dump(params, f, indent=2)
    # Run tracking with worker-specific params and metrics files
    metrics_path = get_worker_metrics_path(worker_id)
    start = time.time()
    try:
        print(
            f"Worker {worker_id} | Trial {trial_number} running tracking command with --params {params_path} --metrics {metrics_path}"
        )
        subprocess.run(
            TRACKING_CMD
            + ["--params", str(params_path), "--metrics", str(metrics_path)],
            check=True,
        )
        elapsed = round(time.time() - start, 2)
        print(
            f"Worker {worker_id} | Trial {trial_number} execution time: {elapsed:.1f}s"
        )
        return update_metrics_csv(
            params, elapsed, trial_number, worker_id, param_hash=param_hash
        )
    except subprocess.CalledProcessError:
        print(
            f"[ERROR] Worker {worker_id} | Trial {trial_number}: basf2 execution failed."
        )
        return 0.0


# --- Objective Function ---
def trial_objective(trial_number, param_values, worker_id=None):
    """Convert parameter values to dictionary, run tracking, and return F1 score."""
    global _trial_counter

    # If worker_id is None, use the global worker ID
    if worker_id is None:
        worker_id = _worker_id
        _trial_counter += 1
        trial_number = _trial_counter

    # Convert tuple of parameter values to dictionary
    params = dict(zip(PARAM_SPACE.keys(), param_values))
    param_hash = compute_param_hash(params)

    logger.info(
        f"[TRIAL START] Worker {worker_id} | Trial {trial_number} | param_hash: {param_hash} | Params: {params}"
    )

    # Run tracking with parameters
    f1_score = run_tracking_with_params(
        params, trial_number, worker_id, param_hash=param_hash
    )

    logger.info(
        f"[TRIAL END] Worker {worker_id} | Trial {trial_number} | F1: {f1_score:.4f} | param_hash: {param_hash}"
    )
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
        "--cluster",
        action="store_true",
        default=False,
        help="Running as part of a cluster job array (Slurm or LSF)",
    )
    args = parser.parse_args()

    # Get cluster job ID and total jobs if running on a cluster (Slurm or LSF)
    if args.cluster:
        # Check for Slurm environment variables
        if "SLURM_ARRAY_TASK_ID" in os.environ:
            job_id = int(os.environ.get("SLURM_ARRAY_TASK_ID", "0"))
            n_jobs = int(os.environ.get("SLURM_ARRAY_TASK_COUNT", "1"))
            cluster_type = "Slurm"
        # Check for LSF environment variables
        elif "LSB_JOBINDEX" in os.environ:
            job_id = int(os.environ.get("LSB_JOBINDEX", "0")) - 1  # LSF is 1-indexed
            # For LSF, we need to calculate total jobs differently
            # LSB_JOBINDEX_END gives the last index in the job array
            if "LSB_JOBINDEX_END" in os.environ:
                n_jobs = int(os.environ.get("LSB_JOBINDEX_END", "1"))
            else:
                # If LSB_JOBINDEX_END is not available, try to get from LSB_JOBINDEX_STEP
                step = int(os.environ.get("LSB_JOBINDEX_STEP", "1"))
                start = int(os.environ.get("LSB_JOBINDEX_START", "1"))
                end = int(os.environ.get("LSB_JOBINDEX_END", start))
                n_jobs = (end - start) // step + 1
            cluster_type = "LSF"
        else:
            # Fallback if no recognized environment variables are found
            job_id = 0
            n_jobs = 1
            cluster_type = "Unknown"

        print(f"[INFO] Running as {cluster_type} job {job_id} of {n_jobs}")

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

        # Worker metrics file will be created by update_metrics_csv when needed

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

            # Worker metrics files will be created by update_metrics_csv when needed

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
