#!/usr/bin/env python3

import argparse
import itertools
import json
import os
import sys
from pathlib import Path
from multiprocessing import Pool
import logging

from src.scipy_opt_utils import (
    PARAM_SPACE,
    METRICS_FIELDS,
    TRACKING_CMD,
    init_worker,
    get_worker_metrics_path,
    update_metrics_csv,
    run_tracking_with_params,
    merge_worker_metrics,
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


# Objective Function
def trial_objective(trial_number, param_values, worker_id=None):
    """
    Convert parameter values to dictionary, run tracking, and return F1 score.

    Parameters:
    trial_number (int): Trial number.
    param_values (tuple): Tuple of parameter values.
    worker_id (int): Worker ID (optional).

    Returns:
    tuple: (F1 score, elapsed time)
    """
    global _trial_counter

    # If worker_id is None, use the global worker ID
    if worker_id is None:
        worker_id = _worker_id
        _trial_counter += 1
        trial_number = _trial_counter

    # Convert tuple of parameter values to dictionary
    params = dict(zip(PARAM_SPACE.keys(), param_values))

    logger.info(f"[TRIAL START] Worker {worker_id} | Trial {trial_number}")

    # Run tracking with parameters
    f1_score, elapsed = run_tracking_with_params(
        params, trial_number, worker_id, TRACKING_CMD
    )

    # Update metrics with trial results
    update_metrics_csv(
        params=params,  # Parameters first
        f1=f1_score,  # Then metrics
        elapsed=elapsed,  # Then execution info
        worker_id=worker_id,
        trial_number=trial_number,
    )

    logger.info(
        f"[TRIAL END] Worker {worker_id} | Trial {trial_number} | F1: {f1_score:.4f} | Time: {elapsed:.1f}s"
    )

    return f1_score, elapsed


def print_grid_summary(n_jobs=None):
    """Print a summary of the grid search space and job distribution."""
    header = "Grid Search Summary"
    separator = "=" * 60
    print(f"\n{separator}\n{header}\n{separator}")

    # Parameter space summary
    print("\nParameter Space:")
    print("-" * 20)
    total_combinations = 1
    for param, values in PARAM_SPACE.items():
        n_values = len(values)
        total_combinations *= n_values
        print(f"{param}:")
        print(f"  Values: {values}")
        print(f"  Unique values: {n_values}")

    print("\nGrid Statistics:")
    print("-" * 20)
    print(f"Total parameter combinations: {NUM_GRID_POINTS}")
    print("Each combination = 1 trial")

    if n_jobs:
        print("\nJob Distribution:")
        print("-" * 20)
        trials_per_job = (NUM_GRID_POINTS + n_jobs - 1) // n_jobs
        print(f"Number of jobs: {n_jobs}")
        print(f"Trials per job: {trials_per_job}")

        # Show job ranges
        print("\nJob Assignments:")
        for job in range(n_jobs):
            start = job * trials_per_job + 1
            end = min((job + 1) * trials_per_job, NUM_GRID_POINTS)
            if start > NUM_GRID_POINTS:
                print(f"  Job {job+1:2d}: No trials (grid exhausted)")
            else:
                n_trials = end - start + 1
                print(
                    f"  Job {job+1:2d}: Trials {start:3d} to {end:3d} ({n_trials:2d} trials)"
                )

    print("\n" + "=" * 60)


def main():
    """Main function to run grid search in various modes.
    Supports:
    1. Cluster mode (LSF or Slurm)
    2. Local multiprocessing
    3. Single worker
    """
    # Parse arguments
    parser = argparse.ArgumentParser(description="Grid Search.")
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers",
    )
    parser.add_argument(
        "--cluster",
        action="store_true",
        help="Run in cluster mode (LSF or Slurm)",
    )
    args = parser.parse_args()

    # Create debug directory for results
    debug_dir = Path("debug")
    debug_dir.mkdir(exist_ok=True)

    # Common function to print/save results
    def save_results(best_score, best_params, job_id=None, trial_num=None):
        logger.info("\nGrid search complete.")
        if best_params:
            if job_id:
                logger.info(f"Best result from Job {job_id} (Trial {trial_num})")
            logger.info("Best Parameters:")
            best_params_dict = (
                dict(zip(PARAM_SPACE.keys(), best_params))
                if isinstance(best_params, tuple)
                else best_params
            )
            for param_name, value in best_params_dict.items():
                logger.info(f"  {param_name}: {value}")
            logger.info(f"\n🏆 Best F1 Score: {best_score:.4f}\n")

            # Save best parameters
            with Path("best_params.json").open("w") as f:
                json.dump(best_params_dict, f, indent=2)
            logger.info("Best parameters saved to best_params.json")

            return best_params_dict

    # Handle LSF/Slurm job array execution
    if args.cluster:
        # Get cluster job ID and total jobs
        if "LSB_JOBINDEX" in os.environ:  # LSF
            job_id = int(os.environ["LSB_JOBINDEX"])
            n_jobs = int(os.environ["LSB_JOBINDEX_END"])
            logger.info(f"Running as LSF job {job_id}/{n_jobs}")
        elif "SLURM_ARRAY_TASK_ID" in os.environ:  # Slurm
            job_id = int(os.environ["SLURM_ARRAY_TASK_ID"])
            n_jobs = int(os.environ["SLURM_ARRAY_TASK_COUNT"])
            logger.info(f"Running as Slurm job {job_id}/{n_jobs}")
        else:
            raise RuntimeError("No cluster environment variables found")

        # Calculate chunk for this job
        trials_per_job = (NUM_GRID_POINTS + n_jobs - 1) // n_jobs
        start_trial = (job_id - 1) * trials_per_job
        end_trial = min(start_trial + trials_per_job, NUM_GRID_POINTS)
        grid_subset = GRID[start_trial:end_trial]

        # Skip if no trials to process
        if not grid_subset:
            logger.info(f"Job {job_id} has no trials to process (grid exhausted)")
            sys.exit(0)

        logger.info(f"Job {job_id} processing trials {start_trial+1} to {end_trial}")

        # Initialize worker-specific files
        metrics_file = get_worker_metrics_path(job_id)
        if metrics_file.exists():
            metrics_file.unlink()  # Start fresh

        # Process this job's parameter combinations
        best_score = float("-inf")
        best_params = None
        best_trial = None

        for trial_num, param_set in enumerate(grid_subset, start_trial + 1):
            logger.info(f"Processing trial {trial_num}/{NUM_GRID_POINTS}")
            score, elapsed = trial_objective(trial_num, param_set, job_id)

            if score > best_score:
                best_score = score
                best_params = param_set
                best_trial = trial_num

        # Save this job's best results
        job_result = {
            "job_id": job_id + 1,
            "best_score": best_score,
            "best_params": dict(zip(PARAM_SPACE.keys(), best_params)),
            "best_trial": best_trial,
            "trials_processed": len(grid_subset),
        }

        results_file = Path(f"job_results_{job_id+1:02d}.json")
        with results_file.open("w") as f:
            json.dump(job_result, f, indent=2)

        print(f"\n[INFO] Job {job_id+1} complete")
        print(f"Best score: {best_score:.4f} (trial {best_trial})")

        # If this is the last job, merge all results while keeping originals
        if job_id == n_jobs - 1:
            print("\n[INFO] Last job completed, compiling results...")

            # Create debug directory for job files
            debug_dir = Path("debug_files")
            debug_dir.mkdir(exist_ok=True)

            # Copy all worker metrics to debug directory
            for i in range(n_jobs):
                metrics_file = Path(f"metrics_worker_{i:02d}.csv")
                if metrics_file.exists():
                    debug_metrics = debug_dir / f"metrics_worker_{i:02d}.csv"
                    metrics_file.rename(debug_metrics)

            # Merge metrics into final CSV
            merge_worker_metrics(METRICS_FIELDS, "metrics_final.csv")
            print("[INFO] All metrics merged to metrics_final.csv")
            print(f"[INFO] Individual metrics saved in {debug_dir}/")

            # Compile results from all jobs
            all_results = []
            for i in range(n_jobs):
                result_file = Path(f"job_results_{i+1:02d}.json")
                if result_file.exists():
                    with result_file.open() as f:
                        job_result = json.load(f)
                        all_results.append(job_result)
                    # Move to debug directory
                    debug_result = debug_dir / f"job_results_{i+1:02d}.json"
                    result_file.rename(debug_result)

            if all_results:
                # Find global best
                global_best = max(all_results, key=lambda x: x["best_score"])

                # Save summary of all jobs
                summary = {
                    "global_best": global_best,
                    "all_jobs": [
                        {
                            "job_id": r["job_id"],
                            "trials": r["trials_processed"],
                            "best_score": r["best_score"],
                            "best_trial": r["best_trial"],
                        }
                        for r in all_results
                    ],
                }

                with (debug_dir / "grid_search_summary.json").open("w") as f:
                    json.dump(summary, f, indent=2)

                # Print results
                print("\n[INFO] Grid search complete")
                print(f"Total jobs completed: {len(all_results)}")
                print(
                    f"Total trials processed: {sum(r['trials_processed'] for r in all_results)}"
                )
                print("\nBest results:")
                print(
                    f"Job {global_best['job_id']} (Trial {global_best['best_trial']})"
                )
                print(f"F1 Score: {global_best['best_score']:.4f}")
                print("Parameters:")
                for k, v in global_best["best_params"].items():
                    print(f"  {k}: {v}")

                # Save best parameters
                with Path("best_params.json").open("w") as f:
                    json.dump(global_best["best_params"], f, indent=2)
                print("\nBest parameters saved to best_params.json")
                print(f"Full results available in {debug_dir}/")
                print("Files saved for debugging:")
                print("  - Individual job metrics: metrics_worker_XX.csv")
                print("  - Job results: job_results_XX.json")
                print("  - Grid search summary: grid_search_summary.json")
                best_score = score
                best_params = param_set

    else:
        # Regular local execution
        if args.workers > 1:
            print(f"[INFO] Starting grid search with {args.workers} workers")

            # Worker metrics files will be created by update_metrics_csv when needed

            # Divide grid points among workers
            grid_chunks = [GRID[i :: args.workers] for i in range(args.workers)]

            # Create worker IDs list
            worker_ids = list(range(args.workers))

            # Create pool and run grid search
            with Pool(
                processes=args.workers,
                initializer=init_worker,
                initargs=(worker_ids, logger),
            ) as pool:
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
                results = [r.get() for r in results]  # Each result is (score, elapsed)
                best_idx = max(range(len(results)), key=lambda i: results[i][0])
                best_score = results[best_idx][0]
                best_params = GRID[best_idx]

            # Merge worker metrics files
            merge_worker_metrics(METRICS_FIELDS)

        else:
            # Single worker mode
            print("[INFO] Starting grid search with single worker")
            print(f"[INFO] Processing all {NUM_GRID_POINTS} parameter combinations")

            best_score = -1
            best_params = None

            for i, param_set in enumerate(GRID, 1):
                print(f"[Trial {i}/{NUM_GRID_POINTS}]")
                score, elapsed = trial_objective(i, param_set)

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


if __name__ == "__main__":
    # Get LSF job count if running in cluster
    n_jobs = None
    if "--cluster" in sys.argv and "LSB_JOBINDEX_END" in os.environ:
        n_jobs = int(os.environ["LSB_JOBINDEX_END"])

    # Print grid search summary
    print_grid_summary(n_jobs)

    # Run grid search
    main()
