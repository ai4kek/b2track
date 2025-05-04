"""
Common utilities for Belle II tracking parameter optimization (grid and random search).
All functions in this file are shared between run_scipy_rand.py and run_scipy_grid.py.
Docstrings and comments are unified for consistency.
"""

import atexit
import csv
import hashlib
import json
import logging
import multiprocessing
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "scipy_opt_utils.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(processName)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("scipy_opt_utils")

# Parameter space
PARAM_SPACE = {
    "maximalDeltaPhi": [0.2, 0.3],
    "maximalLayerJump": [4, 6],
    "minimalPtRequirement": [0.0, 0.1],
    "pathMaximalCandidatesInFlight": [2, 3],
    "stateMaximalHitCandidates": [3, 4],
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
def init_worker(worker_ids, logger=None):
    """Initialize worker-specific environment variables and counter.
    Each process gets a worker ID based on its process ID.
    """
    global _worker_id, _trial_counter
    process_idx = multiprocessing.current_process()._identity[0] - 1
    if process_idx < 0:  # Main process
        _worker_id = 0
    else:
        _worker_id = worker_ids[process_idx % len(worker_ids)]
    _trial_counter = 0
    os.environ["WORKER_ID"] = str(_worker_id)
    if logger:
        logger.info(f"Worker {_worker_id} initialized (PID: {os.getpid()})")


def compute_param_hash(params):
    """Compute a short hash for the given parameter set."""
    param_str = json.dumps(params, sort_keys=True)
    return hashlib.sha1(param_str.encode()).hexdigest()[:10]


def get_worker_params_path(worker_id):
    """Get the worker-specific parameters file path."""
    if worker_id is None:
        raise ValueError("Worker ID must be provided")
    return Path(f"params_worker_{worker_id:03d}.json")


def get_worker_metrics_path(worker_id):
    """Get the worker-specific metrics file path."""
    if worker_id is None:
        raise ValueError("Worker ID must be provided")
    return Path(f"metrics_worker_{worker_id:03d}.csv")


def cleanup_worker_files():
    """Clean up worker-specific files (params and metrics)."""
    # Clean parameter files
    for param_file in Path().glob("params_worker_*.json"):
        param_file.unlink(missing_ok=True)
    # Clean metrics files
    for metrics_file in Path().glob("metrics_worker_*.csv"):
        metrics_file.unlink(missing_ok=True)


def update_worker_metrics(worker_id, trial_number, elapsed, metrics_path):
    """
    Update the most recent (last) row in the metrics CSV with execution_time, worker_id, and trial_number.
    """
    # Read all rows
    with open(metrics_path, "r", newline="") as f:
        reader = list(csv.DictReader(f))
        fieldnames = reader[0].keys() if reader else []

    if not reader:
        raise RuntimeError("Metrics CSV is empty, cannot update last row.")

    # Update the last row
    last_row = reader[-1]
    last_row["execution_time"] = elapsed
    last_row["worker_id"] = worker_id
    last_row["trial_number"] = trial_number

    # Write back all rows
    with open(metrics_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reader)


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
    """Execute tracking pipeline and return resulting F1 score.
    Writes parameters to a worker-specific JSON file, runs the
    tracking command, and parses the F1 score from stdout.

    Args:
        trial_number: Trial sequence number
        worker_id: Worker/job ID
        params_path: Path to parameter JSON file
        metrics_path: Path to metrics CSV file
        max_retries: Maximum number of retries on failure
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

            logger.info(f"Running command: {cmd_str}")

            result = subprocess.run(
                cmd_str,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                encoding="utf-8",
                timeout=3600,  # 1 hour timeout
            )
            elapsed = time.time() - start

            # Parse F1 score from stdout (last line)
            output_lines = result.stdout.strip().split("\n")
            f1_score = float(output_lines[-1])
            return f1_score, elapsed

        except subprocess.TimeoutExpired:
            logger.error(
                f"Trial {trial_number}: Tracking command timed out after 1 hour"
            )
            if attempt < max_retries - 1:
                logger.info(f"Retrying... (attempt {attempt + 1}/{max_retries})")
                time.sleep(5)  # Wait before retry
                continue

        except Exception as e:
            logger.error(f"Trial {trial_number}: Tracking command failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying... (attempt {attempt + 1}/{max_retries})")
                time.sleep(5)  # Wait before retry
                continue

    return 0.0, 0.0


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
