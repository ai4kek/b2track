#!/usr/bin/env python3

"""Belle II Tracking Parameter Grid Search

This script performs a grid search over tracking parameters to optimize F1 score.
It supports three execution modes:

1. Single Worker Mode:
   python3 run_grid.py

2. Multi-Worker Mode (local parallel processing):
   python3 run_scipy_grid.py --workers <N>
   Example: python3 run_grid.py --workers 4

3. LSF Cluster Mode:
   bsub -J "grid[1-<N>]" python3 run_grid.py --cluster
   Example: bsub -J "grid[1-5]" python3 run_grid.py --cluster

   Note: Must be run as an LSF job array. The script uses LSB_JOBINDEX and
   LSB_JOBINDEX_END environment variables to distribute work across workers.

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

import numpy as np

from src.optimization_utils import (
    PARAM_SPACE,
    get_main_logger,
    get_worker_file_path,
    get_worker_logger,
    init_worker,
    run_tracking_with_params,
    update_worker_metrics,
)

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

    # Initialize main logger
    main_logger = get_main_logger()
    main_logger.info("Grid search started")

    # Parse arguments
    parser = argparse.ArgumentParser(description="Grid Search.")
    parser.add_argument(
        "--workers",
        type=int,
        help="Number of workers for local multiprocessing mode",
    )
    parser.add_argument(
        "--arrays",
        type=int,
        help="Number of jobs in the job array for cluster mode",
    )
    args = parser.parse_args()

    # Log grid points and parameter space
    main_logger.info(f"Total grid points to process: {NUM_GRID_POINTS}")
    main_logger.info("Parameter space:")
    for param, values in PARAM_SPACE.items():
        main_logger.info(f"  {param}: {len(values)} values = {values}")

    # ==== Cluster Mode ====
    # Detect if running in LSF cluster environment by checking for LSB_JOBINDEX
    if "LSB_JOBINDEX" in os.environ:

        # LSF uses 1-based indexing for job arrays
        job_id = int(os.environ["LSB_JOBINDEX"])  # Current job index (1-based)

        # In cluster mode, --arrays must be specified
        if args.arrays is None:
            main_logger.error("Error: --arrays parameter is required for cluster mode")
            main_logger.error("Please specify the total number of jobs in the array")
            sys.exit(1)

        # Use the user-specified total number of jobs
        n_total_workers = args.arrays
        main_logger.info(
            f"Cluster mode: Using {n_total_workers} total jobs for chunk calculation"
        )

        # Get the actual number of jobs in the current submission for logging
        n_jobs = int(os.environ.get("LSB_JOBINDEX_END", 1))

        # Get worker logger for status updates
        worker_logger = get_worker_logger(job_id)

        # Log LSF job information
        main_logger.info(f"Grid Search on LSF with {n_jobs} Jobs")
        main_logger.info(f"Worker {job_id} started for distributed processing")

        worker_logger.info(f"Worker {job_id} started for distributed processing")
        worker_logger.info(f"Worker {job_id} is one of {n_total_workers} total workers")

        # Clean old worker files
        # cleanup_worker_files(job_id)

        # LSF job_id is already 1-based, use it directly
        worker_id = job_id  # 1-based worker ID

        # Calculate base chunk size and remainder based on the total number of workers
        # This ensures each worker gets the same chunk regardless of resubmission
        base_chunk_size = NUM_GRID_POINTS // n_total_workers
        remainder = NUM_GRID_POINTS % n_total_workers

        # Calculate this worker's exact chunk boundaries
        # Workers 1 to remainder get one extra trial each
        start_idx = (worker_id - 1) * base_chunk_size + min(worker_id - 1, remainder)
        end_idx = start_idx + base_chunk_size + (1 if worker_id <= remainder else 0)

        # Log distribution details in main logger
        main_logger.info(
            f"Distribution strategy for {NUM_GRID_POINTS} trials across {n_total_workers} total workers:"
        )
        main_logger.info(
            f"Current job is worker {job_id} of {n_jobs} in this submission"
        )
        main_logger.info(f"  - Base chunk size: {base_chunk_size} trials per worker")
        if remainder > 0:
            main_logger.info(
                f"  - First {remainder} workers get {base_chunk_size + 1} trials"
            )
            main_logger.info(f"  - Remaining workers get {base_chunk_size} trials")
        else:
            main_logger.info("  - All workers get exactly same number of trials")

        # Log this worker's specific assignment
        worker_logger.info(f"Worker {worker_id} assignment details:")

        # Exit early if this worker has no trials to process
        if start_idx >= NUM_GRID_POINTS:
            msg = f"Worker {worker_id} has no trials to process (all {NUM_GRID_POINTS} have been assigned already)"
            worker_logger.warning(msg)
            main_logger.warning(msg)
            return

        # Log assignment details for workers with trials
        worker_logger.info(
            f"  - Processing trials {start_idx+1} to {end_idx} ({end_idx-start_idx} trials)"
        )
        worker_logger.info(
            f"  - This is a {'larger' if worker_id <= remainder else 'standard'} chunk"
        )

        # Log parameter combinations for this worker
        worker_logger.info("First trial parameters in this worker's chunk:")
        param_names = list(PARAM_SPACE.keys())
        first_params = dict(zip(param_names, GRID[start_idx]))
        for param, value in first_params.items():
            worker_logger.info(f"  - {param}: {value}")

        # Get this worker's chunk of trials
        job_chunk = GRID[start_idx:end_idx]

        try:
            # Process the chunk
            trials_processed = process_chunk(job_id, job_chunk)
            msg = f"Worker {job_id} completed {trials_processed} out of {len(job_chunk)} trials"
            worker_logger.info(msg)

            # Check if any trials failed
            if trials_processed < len(job_chunk):
                failed_trials = len(job_chunk) - trials_processed
                msg = f"Worker {job_id} failed to process {failed_trials} trials"
                worker_logger.warning(msg)
                main_logger.warning(msg)

        except Exception as e:
            msg = f"Worker {job_id} failed with error: {e}"
            worker_logger.error(msg)
            main_logger.error(msg)

        # Log completion
        msg = f"Worker {job_id} completed processing"
        worker_logger.info(msg)
        main_logger.info(msg)

    else:
        # ==== Local Mode ====
        # In local mode, --workers must be specified for multi-worker mode
        if args.workers is None:
            # Default to single worker if not specified
            args.workers = 1
            main_logger.info(
                "No worker count specified, defaulting to single worker mode"
            )

        # Multi-worker mode if workers > 1
        if args.workers > 1:
            main_logger.info(f"Local multi-worker mode: Using {args.workers} workers")
            main_logger.info(
                f"Starting {args.workers} workers for distributed processing"
            )

            # In local mode, --workers determines the total number of workers
            n_total_workers = args.workers

            # Calculate base chunk size and remainder for even distribution
            base_chunk_size = NUM_GRID_POINTS // args.workers
            remainder = NUM_GRID_POINTS % args.workers

            # Create chunks with 1-based worker IDs
            worker_args = []

            # Log distribution strategy
            main_logger.info(
                f"Distribution strategy for {NUM_GRID_POINTS} trials across {args.workers} workers:"
            )
            main_logger.info(
                f"  - Base chunk size: {base_chunk_size} trials per worker"
            )
            if remainder > 0:
                main_logger.info(
                    f"  - First {remainder} workers get {base_chunk_size + 1} trials"
                )
                main_logger.info(f"  - Remaining workers get {base_chunk_size} trials")
            else:
                main_logger.info("  - All workers get exactly same number of trials")

            for worker_id in range(1, args.workers + 1):  # 1-based worker IDs
                # Calculate exact chunk boundaries for this worker
                start_idx = (worker_id - 1) * base_chunk_size + min(
                    worker_id - 1, remainder
                )
                end_idx = (
                    start_idx + base_chunk_size + (1 if worker_id <= remainder else 0)
                )

                if start_idx < NUM_GRID_POINTS:
                    worker_args.append((worker_id, GRID[start_idx:end_idx]))
                    main_logger.info(
                        f"Worker {worker_id} assignment: trials {start_idx+1} to {end_idx} "
                        f"({end_idx-start_idx} trials, {'larger' if worker_id <= remainder else 'standard'} chunk)"
                    )

            # Create pool and run grid search
            try:
                with Pool(processes=args.workers) as pool:
                    # Use starmap to assign each chunk to a worker
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

            except Exception as e:
                main_logger.error(f"Distributed processing failed with error: {e}")
                # Even if some workers fail, try to merge available results
                main_logger.info(
                    "Attempting to merge available results from successful workers"
                )

            finally:
                main_logger.info(
                    "Multi-worker processing completed - worker files preserved for merging"
                )

        # ==== Single Worker Mode ====
        else:
            # Single worker mode (only when --workers is not specified)
            main_logger.info("Grid Search with Single Worker")
            main_logger.info("Starting worker 1 for sequential processing")
            main_logger.info(f"Processing {NUM_GRID_POINTS} trials sequentially")

            # Process all trials using worker_id=1 (1-based)
            worker_id = 1  # Always use worker_id 1 for single worker mode
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
