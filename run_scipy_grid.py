#!/usr/bin/env python3

"""
Belle II Tracking Parameter Grid Search

This script performs a grid search over tracking parameters to optimize F1 score.
It supports three execution modes:

1. Single Worker Mode:
   python3 run_scipy_grid.py

2. Multi-Worker Mode (local parallel processing):
   python3 run_scipy_grid.py --workers <N>
   Example: python3 run_scipy_grid.py --workers 4

3. Cluster Mode:
   - LSF: bsub -J "grid[1-<N>]" python3 run_scipy_grid.py --cluster
     Example: bsub -J "grid[1-5]" python3 run_scipy_grid.py --cluster
   - Slurm: sbatch --array=1-<N> run_scipy_grid.py --cluster
     Example: sbatch --array=1-5 run_scipy_grid.py --cluster

Output:
- metrics_all.csv: Contains all results from all workers/jobs
- best_results.json: Contains the parameters with the best F1 score
"""

import argparse
import itertools
import json
import logging
import os
import sys
from multiprocessing import Pool
from pathlib import Path

from src.scipy_opt_utils import (
    METRICS_FIELDS,
    PARAM_SPACE,
    cleanup_worker_files,
    extract_best_results,
    get_worker_metrics_path,
    get_worker_params_path,
    init_worker,
    merge_worker_metrics,
    run_tracking_with_params,
    update_worker_metrics,
)

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "grid_optimizer.log"

# Remove existing log file if it exists
if log_file.exists():
    log_file.unlink()

# Create a logger with the name "grid_optimizer"
logger = logging.getLogger("grid_optimizer")
logger.setLevel(logging.INFO)

# Create handlers
file_handler = logging.FileHandler(log_file)
stream_handler = logging.StreamHandler(sys.stdout)

# Create formatter and add it to the handlers
formatter = logging.Formatter(
    "%(asctime)s - %(processName)s - %(levelname)s - %(message)s"
)
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Generate the grid of all parameter combinations
GRID = list(itertools.product(*[PARAM_SPACE[k] for k in PARAM_SPACE.keys()]))
NUM_GRID_POINTS = len(GRID)


# Objective Function
def process_chunk(worker_id, chunk):
    """
    Process a chunk of parameter sets with the given worker ID.
    Each worker processes its own chunk independently.

    Parameters:
    worker_id (int): The worker ID for this process
    chunk (list): List of parameter sets to process

    Returns:
    int: Number of trials processed
    """
    # Initialize worker environment and logging
    init_worker(worker_id, logger)

    trials_processed = 0
    for i, param_set in enumerate(chunk, 1):
        # Calculate global trial number if needed
        trial_num = i
        logger.info(f"Worker {worker_id} processing trial {trial_num}/{len(chunk)}")

        # Process this parameter set
        trial_objective(trial_num, param_set, worker_id)
        trials_processed += 1

    logger.info(f"Worker {worker_id} completed {trials_processed} trials")
    return trials_processed


def trial_objective(trial_number, param_values, worker_id):
    """
    Convert parameter values to dictionary, run tracking, and update metrics file.

    Parameters:
    trial_number (int): Trial number.
    param_values (tuple): Tuple of parameter values.
    worker_id (int): Worker ID.

    Returns:
    float: Elapsed execution time in seconds
    """
    # Convert tuple of parameter values to dictionary
    params = dict(zip(PARAM_SPACE.keys(), param_values))

    metrics_path = get_worker_metrics_path(worker_id)
    params_path = get_worker_params_path(worker_id)

    # Write parameters to JSON
    with params_path.open("w") as f:
        json.dump(params, f, indent=2)

    # Run tracking with parameters
    elapsed = run_tracking_with_params(
        trial_number, worker_id, params_path, metrics_path
    )

    # Append missing columns to metrics file
    update_worker_metrics(worker_id, trial_number, elapsed, metrics_path)

    return elapsed


def main():
    """Main function to run grid search in various modes.
    Supports:
    1. Cluster mode (LSF or Slurm)
    2. Local multiprocessing
    3. Single worker
    """
    # Clean up any leftover worker files and output files from previous runs
    cleanup_worker_files(clean_output_files=True)

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

        logger.info(f"Grid Search with {n_jobs} Jobs")

        # Calculate chunk for this job
        trials_per_job = (NUM_GRID_POINTS + n_jobs - 1) // n_jobs
        start_trial = (job_id - 1) * trials_per_job
        end_trial = min(start_trial + trials_per_job, NUM_GRID_POINTS)
        grid_subset = GRID[start_trial:end_trial]

        # Initialize worker environment
        init_worker(job_id, logger)

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
        for trial_num, param_set in enumerate(grid_subset, start_trial + 1):
            logger.info(f"Processing trial {trial_num}/{NUM_GRID_POINTS}")
            trial_objective(trial_num, param_set, job_id)

        logger.info(f"Job {job_id} complete - processed {len(grid_subset)} trials")

        # If this is the last job, merge all results
        if job_id == n_jobs - 1:
            logger.info("Last job completed, compiling results...")

            # Merge metrics into final CSV
            merge_worker_metrics(METRICS_FIELDS, "metrics_all.csv")
            logger.info("All metrics merged to metrics_all.csv")
            logger.info(f"Total jobs completed: {n_jobs}")
            logger.info(f"Total trials processed: {NUM_GRID_POINTS}")

    else:
        # Regular local execution
        if (
            args.workers >= 1
        ):  # Changed from > 1 to >= 1 to handle --workers 1 the same way
            logger.info(f"Grid Search with {args.workers} Workers")

            # Divide grid points among workers
            grid_chunks = [GRID[i :: args.workers] for i in range(args.workers)]

            # Prepare arguments for each worker: (worker_id, chunk)
            worker_args = [
                (worker_id, chunk) for worker_id, chunk in enumerate(grid_chunks)
            ]

            logger.info(
                f"Distributing {len(GRID)} trials across {args.workers} workers"
            )
            for worker_id, chunk in worker_args:
                logger.info(f"Worker {worker_id} assigned {len(chunk)} trials")

            # Create pool and run grid search - each worker processes its entire chunk
            with Pool(processes=args.workers) as pool:
                # Use starmap to assign each chunk to a worker
                results = pool.starmap(process_chunk, worker_args)

                # Sum up total trials processed
                total_trials = sum(results)

                logger.info(
                    f"Completed {total_trials} trials across {args.workers} workers"
                )

            # Merge worker metrics files
            merge_worker_metrics(METRICS_FIELDS, "metrics_all.csv")
            logger.info("All metrics merged to metrics_all.csv")

        else:
            # Single worker mode (only when --workers is not specified)
            logger.info("Grid Search with Single Worker")
            worker_id = 0

            # Initialize worker environment
            init_worker(worker_id, logger)

            # Process all parameter combinations
            for trial_num, param_set in enumerate(GRID, 1):
                logger.info(f"Processing trial {trial_num}/{NUM_GRID_POINTS}")
                trial_objective(trial_num, param_set, worker_id)

            logger.info(f"Completed {NUM_GRID_POINTS} trials")

            # Merge worker metrics file to metrics_all.csv (for consistency with other modes)
            logger.info("Merging worker metrics to metrics_all.csv...")
            merge_worker_metrics(METRICS_FIELDS, "metrics_all.csv")
            logger.info("Metrics merged to metrics_all.csv")

    # Extract and display best results
    logger.info("Extracting best results from metrics_all.csv...")
    best_results = extract_best_results("metrics_all.csv")

    if best_results is None:
        logger.error("No valid results found in metrics_all.csv")
        logger.error("Grid search completed with errors - no best results available")
        sys.exit(1)

    # Save best results to JSON
    with open("best_results.json", "w") as f:
        json.dump(best_results, f, indent=2)

    logger.info("Grid search completed successfully!")
    logger.info("Best results saved to best_results.json")
    logger.info(f"🏆 Best F1 Score: {best_results['metrics']['f1']:.4f}")
    logger.info("Best Parameters:")
    for param_name, value in best_results["parameters"].items():
        logger.info(f"  {param_name}: {value}")

    # Clean up worker files after successful completion
    cleanup_worker_files()


if __name__ == "__main__":
    # Run the grid search
    main()
