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
import sys
import time
from pathlib import Path

# Configure logging directory
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Standard formatter for all loggers
FORMATTER = logging.Formatter(
    "%(asctime)s - %(processName)s - %(levelname)s - %(message)s"
)


def get_worker_logger(worker_id=None):
    """
    Get a logger for a specific worker or the main process.

    Args:
        worker_id (int, optional): Worker ID. If None, returns the main process logger.

    Returns:
        Logger: A configured logger instance
    """
    if worker_id is None:
        # Main process logger
        logger_name = "grid_main"
        log_file = log_dir / "logs_main.log"
    else:
        # Worker-specific logger
        logger_name = f"grid_worker_{worker_id:03d}"
        log_file = log_dir / f"logs_worker_{worker_id:03d}.log"

    # Create logger
    logger = logging.getLogger(logger_name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        logger.propagate = False  # Don't propagate to parent logger

        # Always add console handler
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(FORMATTER)
        logger.addHandler(stream_handler)

        # Try to add file handler
        try:
            # Remove existing log file if it exists
            if log_file.exists():
                log_file.unlink()

            # Create new file handler
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(FORMATTER)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create log file for {logger_name}: {e}")
            print(f"Continuing with console logging only for {logger_name}")

    return logger


# Create a default logger for the module
logger = get_worker_logger()

# Parameter space
PARAM_SPACE = {
    "maximalDeltaPhi": [0.2, 0.3],
    "maximalLayerJump": [4, 6],
    # "minimalPtRequirement": [0.0, 0.1],
    # "pathMaximalCandidatesInFlight": [2, 3],
    # "stateMaximalHitCandidates": [3, 4],
}

# Metrics fields
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

# Tracking command
TRACKING_CMD = ["basf2", "run_tracking_svd.py", "--"]

# Optimization settings
MAX_TRIALS = 20
RANDOM_SEED = 42


# Helper functions
def init_worker(worker_id):
    """
    Initialize worker environment.

    Args:
        worker_id (int): Worker ID.
    """
    # Set worker ID in environment variables for potential use by subprocesses
    os.environ["WORKER_ID"] = str(worker_id)

    # Get worker-specific logger and log initialization
    logger = get_worker_logger(worker_id)
    logger.info(f"Worker {worker_id} initialized (PID: {os.getpid()})")


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
    """Clean up files for a specific worker.

    Args:
        worker_id (int): Worker ID for file cleanup.
    """
    if worker_id is None:
        raise ValueError("Worker ID must be provided")

    # Clean this worker's files
    for file_type in ["params", "metrics"]:
        worker_file = get_worker_file_path(worker_id, file_type)
        if worker_file.exists():
            worker_file.unlink(missing_ok=True)


def update_worker_metrics(worker_id, trial_number, elapsed, metrics_path):
    """
    Update the most recent (last) row in the metrics CSV with execution_time, worker_id, and trial_number.
    If the file doesn't exist, log a warning and return.
    """
    metrics_path = Path(metrics_path)

    # Check if metrics file exists
    if not metrics_path.exists():
        logger.warning(
            f"Worker {worker_id}, Trial {trial_number}: Metrics file {metrics_path} does not exist. "
            f"Cannot update with execution time {elapsed:.2f}s"
        )
        return

    try:
        # Read all rows
        with open(metrics_path, "r", newline="") as f:
            reader = list(csv.DictReader(f))
            fieldnames = reader[0].keys() if reader else []

        if not reader:
            logger.warning(
                f"Worker {worker_id}, Trial {trial_number}: Metrics file {metrics_path} is empty. "
                f"Cannot update with execution time {elapsed:.2f}s"
            )
            return

        # Update the last row
        last_row = reader[-1]
        last_row["execution_time"] = f"{elapsed:.2f}"  # Format with 2 decimal places
        last_row["worker_id"] = worker_id
        last_row["trial_number"] = trial_number

        # Create a temporary file in the same directory
        temp_path = metrics_path.with_suffix(".tmp")

        # Write to the temporary file
        with open(temp_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(reader)

        # Rename the temporary file to the original file (atomic operation on most systems)
        temp_path.replace(metrics_path)

        logger.info(
            f"Worker {worker_id}, Trial {trial_number}: Updated metrics with execution time {elapsed:.2f}s"
        )
    except Exception as e:
        logger.error(
            f"Worker {worker_id}, Trial {trial_number}: Error updating metrics file {metrics_path}: {e}"
        )


def merge_worker_metrics(metrics_fields, output_file="metrics_all.csv"):
    """Merge all worker metrics files into a single metrics.csv, sorted by worker and trial.

    Handles missing or incomplete files gracefully. If a file cannot be read or
    is missing expected columns, it will be skipped with a warning.

    Args:
        metrics_fields: List of field names for the CSV
        output_file: Path to the output merged file

    Returns:
        bool: True if at least one row was merged, False otherwise
    """
    all_rows = []
    worker_files = sorted(Path().glob("metrics_worker_*.csv"))

    if not worker_files:
        logger.warning("No worker metrics files found to merge")
        return False

    for worker_file in worker_files:
        try:
            with worker_file.open() as f:
                reader = csv.DictReader(f)

                # Verify the file has the expected structure
                if not set(metrics_fields).issubset(set(reader.fieldnames or [])):
                    logger.warning(f"Skipping {worker_file}: missing required columns")
                    continue

                file_rows = list(reader)
                if not file_rows:
                    logger.warning(
                        f"Skipping {worker_file}: file is empty or has only header"
                    )
                    continue

                all_rows.extend(file_rows)
                logger.info(f"Merged {len(file_rows)} rows from {worker_file}")
        except Exception as e:
            logger.warning(f"Error reading {worker_file}: {e}")
            continue

    if not all_rows:
        logger.warning("No valid rows found in any worker metrics files")
        return False

    # Sort by worker_id and trial_number if present
    all_rows.sort(
        key=lambda x: (int(x.get("worker_id", 0)), int(x.get("trial_number", 0)))
    )

    with Path(output_file).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=metrics_fields)
        writer.writeheader()
        writer.writerows(all_rows)

    logger.info(f"Successfully merged {len(all_rows)} rows into {output_file}")
    return len(all_rows) > 0


def extract_best_results(metrics_file="metrics_all.csv"):
    """Extract the best results from the merged metrics file.

    Args:
        metrics_file: Path to the metrics CSV file

    Returns:
        dict: A dictionary containing the best parameters, F1 score, and other metrics
              or None if the file doesn't exist or has no valid rows
    """
    metrics_path = Path(metrics_file)
    if not metrics_path.exists():
        logger.warning(f"Metrics file {metrics_file} does not exist")
        return None

    try:
        with metrics_path.open("r", newline="") as f:
            reader = csv.DictReader(f)

            # Check if the file has the required columns
            if not reader.fieldnames or "f1" not in reader.fieldnames:
                logger.warning(
                    f"Metrics file {metrics_file} is missing required columns"
                )
                return None

            rows = list(reader)
    except Exception as e:
        logger.error(f"Error reading metrics file {metrics_file}: {e}")
        return None

    if not rows:
        logger.warning(f"No data rows found in metrics file {metrics_file}")
        return None

    # Filter out rows with invalid F1 scores
    valid_rows = []
    for row in rows:
        try:
            f1 = float(row.get("f1", 0))
            if f1 >= 0:
                valid_rows.append(row)
            else:
                logger.warning(f"Skipping row with invalid F1 score: {row}")
        except (ValueError, TypeError):
            logger.warning(f"Skipping row with non-numeric F1 score: {row}")
            continue

    if not valid_rows:
        logger.warning(f"No valid rows with F1 scores found in {metrics_file}")
        return None

    # Find the row with the highest F1 score
    best_row = max(valid_rows, key=lambda x: float(x.get("f1", 0)))
    logger.info(f"Found best result with F1 score: {best_row.get('f1')}")

    # Extract parameter values (all fields except metrics and execution info)
    param_fields = [
        f
        for f in best_row.keys()
        if f
        not in [
            "efficiency",
            "purity",
            "f1",
            "finalstate",
            "execution_time",
            "worker_id",
            "trial_number",
        ]
    ]

    best_params = {k: best_row[k] for k in param_fields}

    # Create results dictionary
    best_results = {
        "parameters": best_params,
        "metrics": {
            "f1": float(best_row.get("f1", 0)),
            "efficiency": float(best_row.get("efficiency", 0)),
            "purity": float(best_row.get("purity", 0)),
            "finalstate": best_row.get("finalstate", ""),
        },
        "execution": {
            "worker_id": int(best_row.get("worker_id", 0)),
            "trial_number": int(best_row.get("trial_number", 0)),
            "execution_time": float(best_row.get("execution_time", 0)),
        },
    }

    return best_results


def run_tracking_with_params(
    trial_number, worker_id, params_path, metrics_path, max_retries=3
):
    """Execute tracking pipeline and return execution time.
    Writes parameters to a worker-specific JSON file and runs the tracking command.
    The F1 score is written directly to the metrics file by the tracking command.

    Args:
        trial_number: Trial sequence number
        worker_id: Worker/job ID
        params_path: Path to parameter JSON file
        metrics_path: Path to metrics CSV file
        max_retries: Maximum number of retries on failure

    Returns:
        float: Elapsed execution time in seconds
    """

    for attempt in range(max_retries):
        start = time.time()
        try:
            # Construct the command with proper arguments
            cmd = TRACKING_CMD + [
                f"--params={params_path}",
                f"--metrics={metrics_path}",
            ]

            # Convert command list to string for shell=True
            cmd_str = " ".join(cmd)

            logger.info(f"Worker {worker_id}: Running command: {cmd_str}")

            # Run the command and display output
            result = subprocess.run(
                cmd_str,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,  # This will raise an exception if the command fails
                encoding="utf-8",
                timeout=3600,  # 1 hour timeout
            )

            # Log the output from run_tracking_svd.py
            if result.stdout:
                logger.info(
                    f"Worker {worker_id}, Trial {trial_number} stdout:\n{result.stdout}"
                )
            if result.stderr:
                logger.warning(
                    f"Worker {worker_id}, Trial {trial_number} stderr:\n{result.stderr}"
                )
            elapsed = time.time() - start

            # Return elapsed time
            return elapsed

        except subprocess.TimeoutExpired:
            logger.error(
                f"Worker {worker_id}, Trial {trial_number}: Tracking command timed out after 1 hour"
            )
            if attempt < max_retries - 1:
                logger.info(f"Retrying... (attempt {attempt + 1}/{max_retries})")
                time.sleep(5)  # Wait before retry
                continue

        except Exception as e:
            logger.error(
                f"Worker {worker_id}, Trial {trial_number}: Tracking command failed: {e}"
            )
            if attempt < max_retries - 1:
                logger.info(f"Retrying... (attempt {attempt + 1}/{max_retries})")
                time.sleep(5)  # Wait before retry
                continue

    # If all attempts failed, create a minimal metrics file with failure information
    # This ensures update_worker_metrics will have something to update
    logger.error(
        f"Worker {worker_id}, Trial {trial_number}: All {max_retries} attempts failed"
    )

    # Check if metrics file exists, if not create a minimal one
    if not Path(metrics_path).exists():
        try:
            # Load parameters from the params file
            with open(params_path, "r") as f:
                params = json.load(f)

            # Create a minimal metrics file with the parameters and default metrics
            with open(metrics_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=METRICS_FIELDS)
                writer.writeheader()

                # Create a row with parameters and default metrics
                row = {
                    **params,  # Parameters from JSON
                    "efficiency": "0.0000",  # Default efficiency
                    "purity": "0.0000",  # Default purity
                    "f1": "0.0000",  # Default F1 score
                    "finalstate": "failed",  # Mark as failed
                    "execution_time": "",  # Will be updated by update_worker_metrics
                    "worker_id": "",  # Will be updated by update_worker_metrics
                    "trial_number": "",  # Will be updated by update_worker_metrics
                }
                writer.writerow(row)

            logger.info(
                f"Worker {worker_id}, Trial {trial_number}: Created minimal metrics file after failure"
            )
        except Exception as e:
            logger.error(
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
