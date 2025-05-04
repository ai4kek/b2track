#!/usr/bin/env python3

import argparse
import csv
import json
import os
import subprocess
import time
from pathlib import Path

import optuna
import ray
from ray import tune
from ray.tune.schedulers import ASHAScheduler
from ray.tune.search.optuna import OptunaSearch

from src.optimization_config import (
    MAX_TRIALS,
    METRICS_FIELDS,
    METRICS_PATH,
    PARAM_SPACE,
    PARAMS_PATH,
    RANDOM_SEED,
    TRACKING_CMD,
)


# --- Worker Management ---
def get_worker_metrics_path(worker_id=None):
    """Get path to worker-specific metrics file."""
    if worker_id is None:
        return METRICS_PATH
    return Path(f"metrics_worker_{worker_id:02d}.csv")


def init_metrics_csv(worker_id=None):
    """Initialize metrics CSV file with header if it doesn't exist."""
    metrics_path = get_worker_metrics_path(worker_id)
    with metrics_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=METRICS_FIELDS)
        writer.writeheader()


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
        with METRICS_PATH.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=METRICS_FIELDS)
            writer.writeheader()
            writer.writerows(all_rows)


def update_metrics_csv(params, elapsed, trial_number, worker_id=None):
    """Thread-safe function to update metrics CSV with parameters and execution time, returning F1 score."""
    try:
        trial_metrics = f"metrics_trial_{trial_number:03d}.csv"
        trial_metrics_path = Path(trial_metrics)

        # Read trial metrics file
        with trial_metrics_path.open("r", newline="") as f:
            reader = csv.DictReader(f)
            row = list(reader)[-1]
            f1_score = float(row["f1_score"])

        # Update execution time and parameters
        row["execution_time"] = f"{elapsed:.2f}"
        for key, value in params.items():
            row[key] = str(value)

        # Append to worker-specific metrics file
        worker_metrics = get_worker_metrics_path(worker_id)
        is_first_trial = not worker_metrics.exists()
        with worker_metrics.open("a" if not is_first_trial else "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=METRICS_FIELDS)
            if is_first_trial:
                writer.writeheader()
            writer.writerow(row)

        return f1_score
    except Exception as e:
        print(f"[ERROR] Trial {trial_number}: Error processing metrics: {e}")
        return 0.0
    finally:
        # Clean up trial metrics file
        trial_metrics_path.unlink(missing_ok=True)


def run_tracking_with_params(params, trial_number, worker_id=None):
    """Execute tracking pipeline with given parameters and return resulting F1 score."""
    # Write parameters to JSON
    with PARAMS_PATH.open("w") as f:
        json.dump(params, f, indent=2)

    # Run tracking with trial-specific metrics file
    trial_metrics = f"metrics_trial_{trial_number:03d}.csv"
    start = time.time()
    try:
        cmd = TRACKING_CMD + ["--metrics", trial_metrics]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print(f"[ERROR] Trial {trial_number}: basf2 execution failed.")
        return 0.0
    elapsed = round(time.time() - start, 2)
    print(f"Trial {trial_number} execution time: {elapsed:.1f}s")

    # Update metrics CSV and get F1 score
    return update_metrics_csv(params, elapsed, trial_number, worker_id)


def trial_objective(config, worker_id=None):
    """Run tracking with given parameters and report F1 score to Ray Tune."""
    # Get trial number
    if not hasattr(trial_objective, "counter"):
        trial_objective.counter = 0
    trial_objective.counter += 1
    trial_number = trial_objective.counter

    # Run tracking and get F1 score
    f1_score = run_tracking_with_params(config, trial_number, worker_id)

    # Print trial info
    print(f"Trial {trial_number} | F1: {f1_score:.4f} | Params: {config}")

    # Report score to Ray Tune (we maximize F1 score)
    tune.report(f1_score=f1_score)


def main():
    """Parse arguments, initialize CSV, run Ray Tune optimization with Optuna, and report best parameters."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Ray Tune + Optuna Optimization.")
    parser.add_argument(
        "--trials", type=int, default=MAX_TRIALS, help="Number of trials to run"
    )
    parser.add_argument(
        "--workers", type=int, default=os.cpu_count(), help="Number of parallel workers"
    )
    parser.add_argument(
        "--seed", type=int, default=RANDOM_SEED, help="Random seed for reproducibility"
    )
    parser.add_argument("--slurm", action="store_true", help="Run in Slurm mode")
    args = parser.parse_args()

    # Initialize Ray (with Slurm settings if needed)
    if args.slurm:
        ray.init(address="auto")  # Use Slurm-provided Ray cluster
    else:
        ray.init(num_cpus=args.workers)

    # Set random seeds for reproducibility
    tune.random.seed(args.seed)
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    # Create Optuna sampler with TPE algorithm
    sampler = optuna.samplers.TPESampler(seed=args.seed)

    # Create search space for Ray Tune with Optuna
    # Each parameter is a categorical choice from the PARAM_SPACE list
    search_space = {param: tune.choice(values) for param, values in PARAM_SPACE.items()}

    # Configure ASHA scheduler for early stopping
    scheduler = ASHAScheduler(
        max_t=1,  # Single epoch per trial
        grace_period=1,  # All trials run at least once
        reduction_factor=2,
    )

    # Create Optuna search algorithm
    optuna_search = OptunaSearch(
        space=search_space,
        sampler=sampler,
        metric="f1_score",
        mode="max",
    )

    # Run optimization
    print(f"\n[INFO] Starting Ray Tune + Optuna optimization with {args.trials} trials")
    analysis = tune.run(
        trial_objective,
        search_alg=optuna_search,
        scheduler=scheduler,
        num_samples=args.trials,
        resources_per_trial={"cpu": 1},  # Each trial uses 1 CPU
        local_dir="ray_results",
        name="tracking_optimization_optuna",
        verbose=1,
    )

    # Get best trial
    best_trial = analysis.get_best_trial("f1_score", mode="max")
    best_params = best_trial.config
    best_value = best_trial.last_result["f1_score"]

    # Print results
    print("\n[INFO] Optimization complete.")
    print("Best Parameters:")
    for k, v in best_params.items():
        print(f"  {k}: {v}")
    print(f"\n🏆 Best F1 Score: {best_value:.4f}\n")

    # Save best parameters
    with Path("best_params.json").open("w") as f:
        json.dump(best_params, f, indent=2)
    print("Best parameters saved to best_params.json\n")

    # Clean up Ray
    ray.shutdown()


if __name__ == "__main__":
    main()
