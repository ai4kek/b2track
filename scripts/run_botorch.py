#!/usr/bin/env python3

import argparse
import csv
import json
import os
import subprocess
import time
from pathlib import Path

import torch
from botorch.acquisition import ExpectedImprovement
from botorch.fit import fit_gpytorch_model
from botorch.models import SingleTaskGP
from botorch.optim import optimize_acqf
from gpytorch.mlls import ExactMarginalLogLikelihood

from src.optimization_config import (
    MAX_TRIALS,
    METRICS_FIELDS,
    METRICS_PATH,
    PARAM_SPACE,
    PARAMS_PATH,
    RANDOM_SEED,
    TRACKING_CMD,
)

# --- Configuration ---
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
N_INITIAL_POINTS = 5  # Number of initial random points


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


# --- Update Metrics CSV ---
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


# --- Run Tracking ---
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


# --- Objective Function ---
def trial_objective(parameters):
    """Convert parameter tensor to values, run tracking, and return F1 score for maximization."""
    # Get trial number
    if not hasattr(trial_objective, "counter"):
        trial_objective.counter = 0
    trial_objective.counter += 1
    trial_number = trial_objective.counter

    # Convert parameters tensor to dictionary
    params = {}
    for i, param_name in enumerate(PARAM_SPACE.keys()):
        # Map continuous parameters to discrete choices
        idx = min(
            int(parameters[i].item() * len(PARAM_SPACE[param_name])),
            len(PARAM_SPACE[param_name]) - 1,
        )
        params[param_name] = PARAM_SPACE[param_name][idx]

    # Run tracking and get F1 score
    f1_score = run_tracking_with_params(params, trial_number)

    # Print trial info
    print(f"Trial {trial_number} | F1: {f1_score:.4f} | Params: {params}")

    return torch.tensor([f1_score], device=DEVICE)  # Return as tensor for BoTorch


# --- Main ---
def run_optimization(start_trial, n_trials, init_points, worker_id=None):
    """Run BoTorch optimization for a specific range of trials."""
    # Generate bounds for parameters (all between 0 and 1)
    bounds = torch.stack(
        [
            torch.zeros(len(PARAM_SPACE), device=DEVICE),
            torch.ones(len(PARAM_SPACE), device=DEVICE),
        ]
    )

    # Initialize with random points
    train_x = torch.rand(init_points, len(PARAM_SPACE), device=DEVICE)
    train_obj = torch.zeros(init_points, 1, device=DEVICE)

    # Evaluate initial points
    for i in range(init_points):
        train_obj[i] = trial_objective(train_x[i], worker_id)

    best_value = train_obj.max().item()
    best_idx = train_obj.argmax().item()

    # Run optimization loop
    for i in range(init_points, n_trials):
        # Fit a GP model
        gp = SingleTaskGP(train_x, train_obj)
        mll = ExactMarginalLogLikelihood(gp.likelihood, gp)
        fit_gpytorch_model(mll)

        # Define acquisition function
        acq_func = ExpectedImprovement(gp, best_f=best_value, maximize=True)

        # Optimize acquisition function
        next_point, _ = optimize_acqf(
            acq_function=acq_func,
            bounds=bounds,
            q=1,
            num_restarts=10,
            raw_samples=100,
        )
        next_point = next_point.squeeze(0)

        # Evaluate new point
        new_obj = trial_objective(next_point, worker_id)

        # Update training data
        train_x = torch.cat([train_x, next_point.unsqueeze(0)])
        train_obj = torch.cat([train_obj, new_obj.unsqueeze(0)])

        # Update best value if needed
        if new_obj > best_value:
            best_value = new_obj.item()
            best_idx = i


def main():
    """Parse arguments, initialize CSV, run BoTorch optimization, and report best parameters."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="BoTorch Bayesian Optimization.")
    parser.add_argument(
        "--trials", type=int, default=MAX_TRIALS, help="Number of trials to run"
    )
    parser.add_argument(
        "--workers", type=int, default=os.cpu_count(), help="Number of parallel workers"
    )
    parser.add_argument(
        "--seed", type=int, default=RANDOM_SEED, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--init-points",
        type=int,
        default=N_INITIAL_POINTS,
        help="Number of initial random points",
    )
    parser.add_argument("--slurm", action="store_true", help="Run in Slurm mode")
    args = parser.parse_args()

    # Handle Slurm array job
    if args.slurm:
        # Get Slurm array job ID and total jobs
        job_id = int(os.environ.get("SLURM_ARRAY_TASK_ID", 0))
        n_jobs = int(os.environ.get("SLURM_ARRAY_TASK_COUNT", 1))

        # Calculate trials for this job
        trials_per_job = args.trials // n_jobs
        start_trial = job_id * trials_per_job
        end_trial = start_trial + trials_per_job if job_id < n_jobs - 1 else args.trials

        print(f"[INFO] Job {job_id} handling trials {start_trial} to {end_trial-1}")

        # Initialize worker metrics
        init_metrics_csv(job_id)

        # Set random seed for reproducibility (different per job)
        torch.manual_seed(args.seed + job_id)

        # Run optimization for this job's trials
        run_optimization(
            start_trial=start_trial,
            n_trials=end_trial - start_trial,
            init_points=min(args.init_points, (end_trial - start_trial) // 2),
            worker_id=job_id,
        )

    else:
        # Regular local execution
        os.environ["NUM_WORKERS"] = str(args.workers)
        print(
            f"[INFO] Starting optimization with {args.workers} workers, {args.trials} trials, seed {args.seed}"
        )

        # Initialize worker metrics if using multiple workers
        if args.workers > 1:
            for i in range(args.workers):
                init_metrics_csv(i)
        else:
            init_metrics_csv()

        # Set random seed for reproducibility
        torch.manual_seed(args.seed)

        # Run optimization
        trials_per_worker = args.trials // args.workers
        for i in range(args.workers):
            start_trial = i * trials_per_worker
            end_trial = (
                start_trial + trials_per_worker if i < args.workers - 1 else args.trials
            )

            run_optimization(
                start_trial=start_trial,
                n_trials=end_trial - start_trial,
                init_points=min(args.init_points, (end_trial - start_trial) // 2),
                worker_id=i if args.workers > 1 else None,
            )

        # Merge worker metrics files if using multiple workers
        if args.workers > 1:
            print("\n[INFO] Merging worker metrics files...")
            merge_worker_metrics()

    print("\n[INFO] Optimization complete.")

    # Load all results and find best
    with METRICS_PATH.open("r", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    best_row = max(rows, key=lambda x: float(x["f1_score"]))
    best_params = {k: v for k, v in best_row.items() if k in PARAM_SPACE}
    best_value = float(best_row["f1_score"])

    print("Best Parameters:")
    for k, v in best_params.items():
        print(f"  {k}: {v}")
    print(f"\n🏆 Best F1 Score: {best_value:.4f}\n")

    # Save best parameters
    with Path("best_params.json").open("w") as f:
        json.dump(best_params, f, indent=2)
    print("Best parameters saved to best_params.json\n")


# --- Entry Point ---
if __name__ == "__main__":
    main()
