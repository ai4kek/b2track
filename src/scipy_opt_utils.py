"""
Common utilities for Belle II tracking parameter optimization (grid and random search).
All functions in this file are shared between run_scipy_rand.py and run_scipy_grid.py.
Docstrings and comments are unified for consistency.
"""

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

# Metrics path
METRICS_PATH = Path("metrics.csv")

# CSV fields in order of importance
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


def cleanup_worker_files():
    """Clean up worker-specific files (params and metrics)."""
    # Clean parameter files
    for param_file in Path().glob("params_worker_*.json"):
        param_file.unlink(missing_ok=True)
    # Clean metrics files
    for metrics_file in Path().glob("metrics_worker_*.csv"):
        metrics_file.unlink(missing_ok=True)


def compute_param_hash(params):
    """Compute a short hash for the given parameter set."""
    param_str = json.dumps(params, sort_keys=True)
    return hashlib.sha1(param_str.encode()).hexdigest()[:10]


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


def update_metrics_csv(
    params,
    efficiency=None,
    purity=None,
    f1=None,
    finalstate=None,
    elapsed=0.0,
    worker_id=None,
    trial_number=0,
    metrics_fields=METRICS_FIELDS,
):
    """Update worker-specific metrics CSV with trial results.

    Args in CSV field order:
        params: Parameter dictionary with tracking parameters
        efficiency: Tracking efficiency
        purity: Tracking purity
        f1: F1 score from tracking
        finalstate: Final state type
        elapsed: Execution time in seconds
        worker_id: Worker/job ID
        trial_number: Trial sequence number
        metrics_fields: List of CSV field names (default: METRICS_FIELDS)
    """
    if worker_id is None:
        raise ValueError("Worker ID must be provided for thread-safe operation")

    try:
        # Prepare row data with parameters first
        row = {
            # Add parameters
            **{k: str(v) for k, v in params.items()},
            # Add metrics
            "efficiency": str(efficiency) if efficiency is not None else "",
            "purity": str(purity) if purity is not None else "",
            "f1": str(f1) if f1 is not None else "",
            "finalstate": finalstate if finalstate else "",
            # Add execution info
            "execution_time": f"{elapsed:.2f}",
            "worker_id": str(worker_id),
            "trial_number": str(trial_number),
        }

        # Get metrics file path
        metrics_file = get_worker_metrics_path(worker_id)
        is_new_file = not metrics_file.exists()

        # Write to CSV
        with metrics_file.open("a" if not is_new_file else "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=metrics_fields)
            if is_new_file:
                writer.writeheader()
            writer.writerow(row)

        return f1 if f1 is not None else 0.0

    except Exception as e:
        logger.error(f"Trial {trial_number}: Error processing metrics: {e}")
        return 0.0


def merge_worker_metrics(metrics_fields, output_file="metrics.csv"):
    """Merge all worker metrics files into a single metrics.csv, sorted by worker and trial."""
    all_rows = []
    for worker_file in sorted(Path().glob("metrics_worker_*.csv")):
        with worker_file.open() as f:
            all_rows.extend(list(csv.DictReader(f)))
    # Sort by worker_id and trial_number if present
    all_rows.sort(key=lambda x: (int(x.get("worker_id", 0)), int(x.get("trial", 0))))
    with Path(output_file).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=metrics_fields)
        writer.writeheader()
        writer.writerows(all_rows)


def run_tracking_with_params(
    params, trial_number, worker_id, tracking_cmd, max_retries=3
):
    """Execute tracking pipeline and return resulting F1 score.
    Writes parameters to a worker-specific JSON file, runs the
    tracking command, and parses the F1 score from stdout.

    Args:
        params: Parameter dictionary
        trial_number: Trial sequence number
        worker_id: Worker/job ID
        tracking_cmd: Command to run tracking
        max_retries: Maximum number of retries on failure
    """
    # Check disk space (need at least 100MB free)
    if Path().stat().st_dev == Path("/").stat().st_dev:  # Same filesystem
        free_space = os.statvfs("/").f_frsize * os.statvfs("/").f_bavail
        if free_space < 100 * 1024 * 1024:  # 100MB
            raise RuntimeError(
                f"Insufficient disk space: {free_space/1024/1024:.1f}MB free"
            )

    params_path = get_worker_params_path(worker_id)
    with params_path.open("w") as f:
        json.dump(params, f, indent=2)

    for attempt in range(max_retries):
        start = time.time()
        try:
            result = subprocess.run(
                tracking_cmd,
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
