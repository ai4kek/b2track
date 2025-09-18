#!/usr/bin/env python3

# FIXME: Random Search script is far behind the Grid Search one. At some point,
# I refactor it in similar manner as the grid search script. I am leaving it
# for the sake of completeness, and a testbed for future development.

import argparse
import csv
import hashlib
import json
import logging
import multiprocessing
import os
import subprocess
import sys
import time
from pathlib import Path

from scipy.optimize import differential_evolution

from src.optimization_utils import (
    MAX_TRIALS,
    METRICS_FIELDS,
    PARAM_SPACE,
    RANDOM_SEED,
    cleanup_worker_files,
    compute_param_hash,
    get_worker_metrics_path,
    init_worker,
    merge_worker_metrics,
    run_tracking_with_params,
    update_metrics_csv,
)

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "optimization.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(processName)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(
        log_file), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("optimizer")

# Initialize global variables for worker tracking
_worker_id = 0
_trial_counter = 0

# Add worker_id and param_hash to metrics fields
METRICS_FIELDS = METRICS_FIELDS + ["worker_id", "param_hash"]


# Objective function
def trial_objective(vector):
    """
    Run a trial with given parameters and return negative F1 score for minimization.

    Parameters
    ----------
    vector : list
        List of parameter values to be used for the trial.

    Returns
    -------
    float
        Negative F1 score of the trial.
    """
    global _trial_counter, _worker_id

    # Convert vector to parameter values
    params = {k: PARAM_SPACE[k][int(round(v))]
              for k, v in zip(PARAM_SPACE, vector)}
    param_hash = compute_param_hash(params)

    # Increment trial counter
    _trial_counter += 1

    # Log at INFO level at the start of the trial
    logger.info(
        f"[TRIAL START] Worker {_worker_id} | Trial {_trial_counter} | param_hash: {param_hash} | Params: {params}"
    )

    # Run tracking and get F1 score
    f1_score = run_tracking_with_params(
        params, _trial_counter, _worker_id, param_hash=param_hash
    )

    logger.info(
        f"[TRIAL END] Worker {_worker_id} | Trial {_trial_counter} | F1: {f1_score:.4f} | param_hash: {param_hash}"
    )

    # Return negative F1 score for minimization
    return -f1_score


# Main function
def main():
    """Run optimization to find best tracking parameters."""

    # Clean up any leftover worker files from previous runs
    cleanup_worker_files()

    logger.info("Starting optimization script")

    parser = argparse.ArgumentParser(
        description="Optimize tracking parameters using SciPy Differential Evolution."
    )
    parser.add_argument(
        "--max-trials",
        type=int,
        default=MAX_TRIALS,
        help="Maximum number of trials as safety limit (default: %(default)s)",
    )
    parser.add_argument(
        "--tol",
        type=float,
        default=0.0001,
        help="Relative tolerance for convergence (default: %(default)s)",
    )
    parser.add_argument(
        "--workers", type=int, default=os.cpu_count(), help="Number of parallel workers"
    )
    parser.add_argument(
        "--seed", type=int, default=RANDOM_SEED, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--cluster",
        action="store_true",
        default=False,
        help="Running as part of a cluster job array (Slurm or LSF)",
    )

    args = parser.parse_args()

    # Setup optimization bounds
    bounds = [(0, len(PARAM_SPACE[k]) - 1) for k in PARAM_SPACE]

    # Get cluster job ID and total jobs if running on a cluster (Slurm or LSF)
    if args.cluster:
        # Check for Slurm environment variables
        if "SLURM_ARRAY_TASK_ID" in os.environ:
            job_id = int(os.environ.get("SLURM_ARRAY_TASK_ID", "0"))
            n_jobs = int(os.environ.get("SLURM_ARRAY_TASK_COUNT", "1"))
            cluster_type = "Slurm"
        # Check for LSF environment variables
        elif "LSB_JOBINDEX" in os.environ:
            job_id = int(os.environ.get("LSB_JOBINDEX", "0")) - \
                1  # LSF is 1-indexed
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

        logger.info(f"Running as {cluster_type} job {job_id} of {n_jobs}")

        # Use job ID as worker ID
        global _worker_id
        _worker_id = job_id
        _trial_counter = 0
        os.environ["WORKER_ID"] = str(job_id)
        os.environ["NUM_WORKERS"] = str(n_jobs)
        logger.info(f"Worker {job_id} initialized")

        # Each job handles its share of trials
        trials_per_job = args.max_trials // n_jobs  # Use max_trials instead of trials
        start_trial = job_id * trials_per_job
        end_trial = (
            start_trial + trials_per_job if job_id < n_jobs - 1 else args.max_trials
        )

        logger.info(
            f"Job {job_id} handling trials {start_trial} to {end_trial-1}")

        # Run optimization with single worker (each cluster job is its own worker)
        result = differential_evolution(
            trial_objective,
            bounds=bounds,
            strategy="best1bin",
            maxiter=end_trial - start_trial,
            polish=False,
            disp=True,
            workers=1,
            seed=args.seed
            + job_id
            + hash(str(time.time())) % 10000,  # More varied seed
            updating="immediate",  # Use immediate updates
            # Ensure population size scales with total jobs
            popsize=max(7, n_jobs),
            mutation=(0.5, 1.0),  # Allow more mutation to explore space
            recombination=0.7,  # Increase recombination probability
            tol=args.tol,  # Stop when converged
        )

    else:
        # Regular local execution
        os.environ["NUM_WORKERS"] = str(args.workers)
        print(
            f"[INFO] Running optimization with {args.workers} workers, {args.max_trials} max trials, seed {args.seed}"
        )

        if args.workers > 1:
            from multiprocessing.pool import Pool

            # Create workers with sequential IDs
            worker_ids = list(range(args.workers))
            with Pool(
                processes=args.workers, initializer=init_worker, initargs=(
                    worker_ids,)
            ) as pool:

                result = differential_evolution(
                    trial_objective,
                    bounds=bounds,
                    strategy="best1bin",
                    maxiter=args.max_trials,
                    polish=False,
                    disp=True,
                    workers=pool.map,
                    seed=args.seed,
                    updating="deferred",
                    tol=args.tol,  # Stop when converged
                )
        else:
            print("[INFO] Running optimization...")
            result = differential_evolution(
                trial_objective,
                bounds=bounds,
                strategy="best1bin",
                maxiter=args.max_trials,
                polish=False,
                disp=True,
                workers=1,
                seed=args.seed + os.getpid(),
                updating="immediate",
                popsize=15,  # Slightly larger population for better exploration
                mutation=(0.5, 1.0),
                recombination=0.7,
                tol=args.tol,  # Stop when converged
            )

    # Clean up worker parameter files
    cleanup_worker_files()

    # Merge worker metrics files
    if args.cluster:
        # In cluster mode, each job creates its own metrics file
        # These will be merged externally after all jobs complete
        logger.info("Metrics saved to worker-specific file")
    else:
        # In local mode, merge all worker metrics files
        logger.info("Merging worker metrics files...")
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
