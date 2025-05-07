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
import os
from multiprocessing import Pool
from pathlib import Path

from src.scipy_opt_utils import (
    METRICS_FIELDS,
    PARAM_SPACE,
    cleanup_worker_files,
    extract_best_results,
    get_worker_file_path,
    get_worker_logger,
    init_worker,
    merge_worker_metrics,
    run_tracking_with_params,
    update_worker_metrics,
)

# Get the main process logger (no worker_id means main process)
main_logger = get_worker_logger()
main_logger.info("Grid search started")

# Generate the grid of all parameter combinations
GRID = list(itertools.product(*[PARAM_SPACE[k] for k in PARAM_SPACE.keys()]))
NUM_GRID_POINTS = len(GRID)


# Objective Function
def process_chunk(worker_id, chunk):
    """
    Process a chunk of parameter combinations.

    Parameters:
    worker_id (int): Worker ID.
    chunk (list): List of parameter combinations to process.

    Returns:
    int: Number of trials processed.
    """
    # Initialize worker environment
    init_worker(worker_id)

    # Get worker-specific logger
    worker_logger = get_worker_logger(worker_id)

    trials_processed = 0
    for i, param_set in enumerate(chunk, 1):
        # Calculate global trial number if needed
        trial_num = i
        worker_logger.info(
            f"Worker {worker_id} processing trial {trial_num}/{len(chunk)}"
        )

        try:
            # Process this parameter set
            elapsed = trial_objective(trial_num, param_set, worker_id)

            # Check if the trial was successful (elapsed > 0)
            if elapsed > 0:
                trials_processed += 1
                worker_logger.info(
                    f"Worker {worker_id} completed trial {trial_num} successfully"
                )
            else:
                worker_logger.warning(
                    f"Worker {worker_id} trial {trial_num} returned zero elapsed time, possible failure"
                )

        except Exception as e:
            worker_logger.error(
                f"Worker {worker_id} trial {trial_num} failed with error: {e}"
            )
            # Continue with the next trial even if this one failed
            continue

    worker_logger.info(f"Worker {worker_id} completed {trials_processed} trials")
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
    worker_logger = get_worker_logger(worker_id)

    # Convert tuple of parameter values to dictionary
    params = dict(zip(PARAM_SPACE.keys(), param_values))

    # Clean old worker files
    cleanup_worker_files(worker_id)

    # Get worker-specific file paths
    metrics_path = get_worker_file_path(worker_id, "metrics")
    params_path = get_worker_file_path(worker_id, "params")

    # Write parameters to JSON file
    try:
        with params_path.open("w") as f:
            json.dump(params, f, indent=2)
    except Exception as e:
        worker_logger.error(f"Failed to write parameter file {params_path}: {e}")
        return 0.0  # Return zero to indicate failure

    # Run tracking with parameters
    elapsed = run_tracking_with_params(
        trial_number, worker_id, params_path, metrics_path
    )

    # Check if metrics file exists before trying to update it
    if metrics_path.exists():
        try:
            # Append missing columns to metrics file
            update_worker_metrics(worker_id, trial_number, elapsed, metrics_path)
            worker_logger.info(
                f"Worker {worker_id} updated trial {trial_number} metrics file successfully"
            )
        except Exception as e:
            worker_logger.error(
                f"Worker {worker_id} failed to update trial {trial_number} metrics file: {e}"
            )
    else:
        worker_logger.error(
            f"Worker {worker_id} metrics file {metrics_path} for trial {trial_number} does not exist."
            f"Cannot update with execution time {elapsed:.2f}s"
        )

    return elapsed


def main():
    """Main function to run grid search in various modes.

    Supports:
    1. Cluster mode (LSF or Slurm)
    2. Local multiprocessing
    3. Local single worker
    """

    # Parse arguments
    parser = argparse.ArgumentParser(description="Grid Search.")
    parser.add_argument(
        "--workers",
        type=int,
        help="Number of parallel workers.",
    )
    parser.add_argument(
        "--cluster",
        action="store_true",
        help="Run in cluster mode (LSF or Slurm)",
    )
    args = parser.parse_args()

    # Clean shared output files
    Path("metrics_all.csv").unlink(missing_ok=True)
    Path("best_results.json").unlink(missing_ok=True)

    # ==== Cluster Mode ====
    if args.cluster:

        # Get cluster job ID and total jobs
        if "LSB_JOBINDEX" in os.environ:  # LSF
            job_id = int(os.environ["LSB_JOBINDEX"])
            n_jobs = int(os.environ["LSB_JOBINDEX_END"])
            cluster_type = "LSF"
        elif "SLURM_ARRAY_TASK_ID" in os.environ:  # Slurm
            job_id = int(os.environ["SLURM_ARRAY_TASK_ID"])
            n_jobs = int(os.environ["SLURM_ARRAY_TASK_COUNT"])
            cluster_type = "Slurm"
        else:
            raise RuntimeError("No cluster environment variables found")

        # Get worker logger for status updates
        worker_logger = get_worker_logger(job_id)

        # Log cluster job information
        main_logger.info(f"Grid Search on {cluster_type} with {n_jobs} Jobs")
        main_logger.info(f"Worker {job_id} started for distributed processing")
        worker_logger.info(f"Worker {job_id} is one of {n_jobs} total workers")

        # Calculate chunk size and get this worker's chunk
        chunk_size = (NUM_GRID_POINTS + n_jobs - 1) // n_jobs
        start_idx = (job_id - 1) * chunk_size
        end_idx = min(job_id * chunk_size, NUM_GRID_POINTS)

        # Process only the trials assigned to this worker
        if start_idx < NUM_GRID_POINTS:
            worker_logger.info(
                f"Worker {job_id} processing trials {start_idx+1} to {end_idx} ({end_idx-start_idx} trials)"
            )
            job_chunk = GRID[start_idx:end_idx]

            try:
                # Process the chunk
                trials_processed = process_chunk(job_id, job_chunk)
                worker_logger.info(
                    f"Worker {job_id} completed {trials_processed} out of {len(job_chunk)} assigned trials"
                )

                # Check if all trials were processed successfully
                if trials_processed < len(job_chunk):
                    failed_trials = len(job_chunk) - trials_processed
                    worker_logger.warning(
                        f"Worker {job_id} failed to process {failed_trials} trials"
                    )
                    main_logger.warning(
                        f"Worker {job_id} failed to process {failed_trials} trials"
                    )

            except Exception as e:
                worker_logger.error(f"Worker {job_id} failed with error: {e}")
                main_logger.error(f"Worker {job_id} failed with error: {e}")
                # Even if the worker fails, try to merge available results
                worker_logger.info(
                    "Attempting to merge available results despite worker failure"
                )
        else:
            worker_logger.warning(
                f"Worker {job_id} has no trials to process (start_idx={start_idx} >= n_grid_points={NUM_GRID_POINTS})"
            )

        # Worker completion message
        worker_logger.info(f"Worker {job_id} results preserved for post-processing")
        main_logger.info(f"Worker {job_id} completed processing")

    else:
        # ==== Multi-Worker Mode ====
        if args.workers is not None and args.workers > 1:

            main_logger.info(f"Grid Search with {args.workers} Local Workers")
            main_logger.info(
                f"Starting {args.workers} workers for distributed processing"
            )
            main_logger.info(f"Distributing {NUM_GRID_POINTS} trials across workers")

            # Calculate chunk size for each worker
            chunk_size = (NUM_GRID_POINTS + args.workers - 1) // args.workers

            # Create chunks with 1-based worker IDs
            worker_args = []
            for i in range(args.workers):
                worker_id = i + 1  # 1-based worker IDs
                start_idx = i * chunk_size
                end_idx = min((i + 1) * chunk_size, NUM_GRID_POINTS)
                if start_idx < NUM_GRID_POINTS:
                    worker_args.append((worker_id, GRID[start_idx:end_idx]))
                    main_logger.info(
                        f"Worker {worker_id} assigned trials {start_idx+1} to {end_idx} ({end_idx-start_idx} trials)"
                    )

            # Create pool and run grid search - each worker processes its entire chunk
            try:
                with Pool(processes=args.workers) as pool:
                    # Use starmap to assign each chunk to a worker
                    # Handle worker failures by setting timeout
                    results = pool.starmap(process_chunk, worker_args)

                    # Check results from all workers
                    total_trials_processed = sum(results)
                    main_logger.info(
                        f"All workers completed. Total trials processed: {total_trials_processed}/{NUM_GRID_POINTS}"
                    )

                    # Check if any trials failed
                    if total_trials_processed < NUM_GRID_POINTS:
                        failed_trials = NUM_GRID_POINTS - total_trials_processed
                        main_logger.warning(
                            f"Failed to process {failed_trials} trials across all workers"
                        )
                        main_logger.warning(
                            f"Failed to process {failed_trials} trials across all workers"
                        )

            except Exception as e:
                main_logger.error(f"Distributed processing failed with error: {e}")
                main_logger.error(f"Distributed processing failed with error: {e}")
                # Even if some workers fail, try to merge available results
                main_logger.info(
                    "Attempting to merge available results from successful workers"
                )

            finally:
                main_logger.info(
                    "Multi-worker processing completed - worker files preserved for merging at the end"
                )

        # ==== Single Worker Mode ====
        else:
            # Single worker mode (only when --workers is not specified)
            main_logger.info("Grid Search with Single Worker")
            main_logger.info("Starting 1 worker for sequential processing")
            main_logger.info(f"Processing {NUM_GRID_POINTS} trials sequentially")

            # Process all trials using process_chunk (use worker_id=1)
            worker_id = 1
            trials_processed = process_chunk(worker_id, GRID)

            # Log completion status
            if trials_processed < NUM_GRID_POINTS:
                failed_trials = NUM_GRID_POINTS - trials_processed
                main_logger.warning(f"Failed to process {failed_trials} trials")
            else:
                main_logger.info(
                    f"Singel worker completed {NUM_GRID_POINTS} trials sequentially"
                )

    # Completion message for all modes
    main_logger.info("Grid search completed")

    # Merge worker metrics
    main_logger.info("Post-analysis on all workers through analyze_metrics.py")


if __name__ == "__main__":
    # Run the grid search
    main()
