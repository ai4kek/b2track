"""
Common utilities for Belle II tracking parameter optimization (grid and random search).
All functions in this file are shared between run_scipy_rand.py and run_scipy_grid.py.
Docstrings and comments are unified for consistency.
"""

import csv
import hashlib
import json
import logging
import os
import subprocess
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

# --- Logging ---
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Standard formatter for all loggers
FORMATTER = logging.Formatter(
    "%(asctime)s - %(processName)s - %(levelname)s - %(message)s"
)

# --- Optimization Parameter Definitions ---
# All parameter ranges for grid/random search
PARAM_SPACE_1 = {
    "maximalDeltaPhi": [0.2, 0.4, 0.5],  # def: 0.3926990
    "maximalLayerJump": [4, 5, 6, 7, 8],  # def: 4
    "minimalPtRequirement": [0.0, 0.1],  # def: 0
    "pathMaximalCandidatesInFlight": [3, 4],  # def: 3
    "stateMaximalHitCandidates": [3, 4, 5],  # def: 4
}

# Quick test space
PARAM_SPACE = {
    "maximalDeltaPhi": [0.2, 0.4],
    "maximalLayerJump": [4, 5],
    "minimalPtRequirement": [0.0],
    "pathMaximalCandidatesInFlight": [3],
    "stateMaximalHitCandidates": [3, 4],
}

# Reference parameter set for baseline comparison
REF_PARAM = {
    "maximalDeltaPhi": 0.4,
    "maximalLayerJump": 4,
    "minimalPtRequirement": 0.0,
    "pathMaximalCandidatesInFlight": 3,
    "stateMaximalHitCandidates": 4,
}

# CSV column order for metrics files
METRICS_FIELDS = [
    # Parameters first (dynamic based on PARAM_SPACE)
    *list(PARAM_SPACE.keys()),
    # Then metrics
    "efficiency",
    "purity",
    "f1",
    "finalstate",
    # Then execution info
    "execution_time",
    "worker_id",
    "trial_number",
]

# Command to run the Belle II tracking pipeline
TRACKING_CMD = ["basf2", "run_tracking_svd.py", "--"]

# General optimization settings
MAX_TRIALS = 20
RANDOM_SEED = 42


# Logger functions
def get_main_logger():
    """
    Get the main process logger (file + stream handlers).
    Used for all logging in the main process (not worker-specific).
    """
    logger_name = "grid_main"
    log_file = log_dir / "logs_main.log"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Remove previous handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # File handler with rotating file handler
    file_handler = RotatingFileHandler(
        filename=log_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
    )
    file_handler.setFormatter(FORMATTER)
    logger.addHandler(file_handler)

    # Stream handler for console output
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(FORMATTER)
    logger.addHandler(stream_handler)
    return logger


def get_worker_logger(worker_id):
    """
    Get a logger for a specific worker (file handler only).
    Each worker writes to its own log file for easier debugging.
    """
    logger_name = f"grid_worker_{worker_id:03d}"
    log_file = log_dir / f"logs_worker_{worker_id:03d}.log"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if logger.hasHandlers():
        logger.handlers.clear()

    # File handler with rotating file handler for worker-specific logs
    file_handler = RotatingFileHandler(
        filename=log_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
    )
    file_handler.setFormatter(FORMATTER)
    logger.addHandler(file_handler)
    return logger


# Helper functions
def init_worker(worker_id):
    """
    Initialize worker environment.
    Sets up environment variable and logs worker startup.
    Args:
        worker_id (int): Worker ID.
    """
    main_logger = get_main_logger()
    worker_logger = get_worker_logger(worker_id)
    os.environ["WORKER_ID"] = str(worker_id)
    worker_logger.info(f"Worker {worker_id} initialized (PID: {os.getpid()})")
    main_logger.info(f"Worker {worker_id} initialized (PID: {os.getpid()})")


def compute_param_hash(params):
    """Compute a short hash for the given parameter set."""
    param_str = json.dumps(params, sort_keys=True)
    return hashlib.sha1(param_str.encode()).hexdigest()[:10]


def get_worker_file_path(worker_id, file_type):
    """Get a worker-specific file path.

    Args:
        worker_id (int): Worker ID for file naming
        file_type (str): Type of file ('params' or 'metrics')

    Returns:
        Path: Path to the worker file
    """
    if worker_id is None:
        raise ValueError("Worker ID must be provided")

    # Map file types to extensions
    extensions = {"params": ".json", "metrics": ".csv"}
    if file_type not in extensions:
        raise ValueError(f"Unknown file type: {file_type}")

    return Path(f"{file_type}_worker_{worker_id:03d}{extensions[file_type]}")


def cleanup_worker_files(worker_id):
    """
    Delete parameter and metrics files for a specific worker.
    Useful for cleaning up after a job or before rerunning.
    Args:
        worker_id (int): Worker ID for file cleanup.
    """
    if worker_id is None:
        raise ValueError("Worker ID must be provided")

    # Remove both params and metrics files for this worker
    for file_type in ["params", "metrics"]:
        worker_file = get_worker_file_path(worker_id, file_type)
        if worker_file.exists():
            worker_file.unlink(missing_ok=True)


def update_worker_metrics(worker_id, trial_number, elapsed, metrics_path):
    """
    Update the most recent (last) row in the metrics CSV with execution_time, worker_id, and trial_number.
    If the file doesn't exist, log a warning and return.
    Called after a worker finishes a trial to record timing and IDs.
    """
    main_logger = get_main_logger()
    metrics_path = Path(metrics_path)
    if not metrics_path.exists():
        main_logger.warning(
            f"Worker {worker_id}, Trial {trial_number}: Metrics file {metrics_path} does not exist. "
            f"Cannot update with execution time {elapsed:.2f}s"
        )
        return
    try:
        # Read all rows from metrics file
        with metrics_path.open("r", newline="") as f:
            reader = list(csv.DictReader(f))
            fieldnames = reader[0].keys() if reader else []
        if not reader:
            main_logger.warning(
                f"Worker {worker_id}, Trial {trial_number}: Metrics file {metrics_path} is empty. "
                f"Cannot update with execution time {elapsed:.2f}s"
            )
            return

        # Update last row with timing and IDs
        last_row = reader[-1]
        last_row["execution_time"] = f"{elapsed:.2f}"
        last_row["worker_id"] = worker_id
        last_row["trial_number"] = trial_number

        # Write updated rows back to file
        with metrics_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(reader)
        main_logger.info(
            f"Worker {worker_id}, Trial {trial_number}: Updated metrics with execution time {elapsed:.2f}s"
        )
    except Exception as e:
        main_logger.error(
            f"Worker {worker_id}, Trial {trial_number}: Error updating metrics file {metrics_path}: {e}"
        )


def run_tracking_with_params(
    trial_number, worker_id, params_path, metrics_path, max_retries=3
):
    """
    Execute the Belle II tracking pipeline for a given parameter set.
    Handles retries and logs all output/errors. Returns elapsed time or 0.0 on failure.
    Args:
        trial_number: Trial sequence number
        worker_id: Worker/job ID
        params_path: Path to parameter JSON file
        metrics_path: Path to metrics CSV file
        max_retries: Maximum number of retries on failure
    Returns:
        float: Elapsed execution time in seconds
    """
    main_logger = get_main_logger()
    for attempt in range(max_retries):
        start = time.time()
        try:
            # Build the command for this trial
            cmd = TRACKING_CMD + [
                f"--params={params_path}",
                f"--metrics={metrics_path}",
            ]
            cmd_str = " ".join(cmd)
            main_logger.info(f"Worker {worker_id}: Running command: {cmd_str}")

            # Run the tracking command (stdout/stderr go to cluster job files)
            subprocess.run(
                cmd_str,
                shell=True,
                check=True,  # This will raise an exception if the command fails
                timeout=3600,  # 1 hour timeout
            )
            elapsed = time.time() - start
            return elapsed
        except subprocess.TimeoutExpired:
            main_logger.error(
                f"Worker {worker_id}, Trial {trial_number}: Tracking command timed out after 1 hour"
            )
            if attempt < max_retries - 1:
                main_logger.info(f"Retrying... (attempt {attempt + 1}/{max_retries})")
                time.sleep(5)  # Wait before retry
                continue
        except Exception as e:
            main_logger.error(
                f"Worker {worker_id}, Trial {trial_number}: Tracking command failed: {e}"
            )
            if attempt < max_retries - 1:
                main_logger.info(f"Retrying... (attempt {attempt + 1}/{max_retries})")
                time.sleep(5)  # Wait before retry
                continue

    # If all attempts failed, create a minimal metrics file with failure information
    # This ensures update_worker_metrics will have something to update
    main_logger.error(
        f"Worker {worker_id}, Trial {trial_number}: All {max_retries} attempts failed"
    )

    # Create a minimal metrics file if missing
    if not Path(metrics_path).exists():
        try:
            with open(params_path, "r") as f:
                params = json.load(f)
            with open(metrics_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=METRICS_FIELDS)
                writer.writeheader()
                # Fill with default/failure values
                row = {
                    **params,
                    "efficiency": "0.0000",
                    "purity": "0.0000",
                    "f1": "0.0000",
                    "finalstate": "failed",
                    "execution_time": "",
                    "worker_id": "",
                    "trial_number": "",
                }
                writer.writerow(row)
            main_logger.info(
                f"Worker {worker_id}, Trial {trial_number}: Created minimal metrics file after failure"
            )
        except Exception as e:
            main_logger.error(
                f"Worker {worker_id}, Trial {trial_number}: Failed to create minimal metrics file: {e}"
            )
    return 0.0


def print_grid_summary(n_jobs=None, NUM_GRID_POINTS=None):
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
