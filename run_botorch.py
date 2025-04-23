#!/usr/bin/env python3

import argparse
import csv
import json
import subprocess
import time
from multiprocessing import Lock
from pathlib import Path

import torch
from botorch.acquisition import ExpectedImprovement
from botorch.fit import fit_gpytorch_model
from botorch.models import SingleTaskGP
from botorch.optim import optimize_acqf
from gpytorch.mlls import ExactMarginalLogLikelihood

from tracking_config import (
    MAX_TRIALS,
    METRICS_FIELDS,
    METRICS_PATH,
    PARAM_SPACE,
    PARAMS_PATH,
    RANDOM_SEED,
    TRACKING_CMD,
)

# Create a global lock for CSV file access
csv_lock = Lock()

# --- Configuration ---
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
N_INITIAL_POINTS = 5  # Number of initial random points


# --- Setup CSV ---
def init_metrics_csv():
    """Initialize metrics CSV file with header if it doesn't exist."""
    with METRICS_PATH.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(METRICS_FIELDS)


# --- Update Metrics CSV ---
def update_metrics_csv(params, elapsed, trial_number):
    """Thread-safe function to update metrics CSV with parameters and execution time, returning F1 score."""
    try:
        with csv_lock:  # Thread-safe lock for parallel workers
            # Read current CSV content
            with METRICS_PATH.open("r", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            if not rows:
                print(f"[ERROR] Trial {trial_number}: No rows found in metrics.csv")
                return 0.0

            # Get F1 score from last row
            last_row = rows[-1]
            try:
                f1_score = float(last_row["f1_score"])
            except (ValueError, KeyError):
                print(f"[ERROR] Trial {trial_number}: Invalid f1_score in metrics.csv")
                f1_score = 0.0

            # Update execution time and parameters in the last row
            last_row["execution_time"] = f"{elapsed:.2f}"
            for key, value in params.items():
                last_row[key] = str(value)

            # Write updated content back to file
            with METRICS_PATH.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=METRICS_FIELDS)
                writer.writeheader()
                writer.writerows(rows)

        return f1_score
    except Exception as e:
        print(f"[ERROR] Trial {trial_number}: Error processing metrics: {e}")
        return 0.0


# --- Run Tracking ---
def run_tracking_with_params(params, trial_number):
    """Execute tracking pipeline with given parameters and return resulting F1 score."""
    # Write parameters to JSON
    with PARAMS_PATH.open("w") as f:
        json.dump(params, f, indent=2)

    # Run tracking command
    start = time.time()
    try:
        subprocess.run(TRACKING_CMD, check=True)
    except subprocess.CalledProcessError:
        print(f"[ERROR] Trial {trial_number}: basf2 execution failed.")
        return 0.0
    elapsed = round(time.time() - start, 2)
    print(f"Trial {trial_number} execution time: {elapsed:.1f}s")

    # Update metrics CSV and get F1 score
    return update_metrics_csv(params, elapsed, trial_number)


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
def main():
    """Parse arguments, initialize CSV, run BoTorch optimization, and report best parameters."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="BoTorch Bayesian Optimization.")
    parser.add_argument(
        "--trials", type=int, default=MAX_TRIALS, help="Number of trials to run"
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
    args = parser.parse_args()

    # Initialize metrics CSV if needed
    if not METRICS_PATH.exists():
        init_metrics_csv()
        print(f"[INFO] Metrics CSV initialized: {METRICS_PATH}")

    # Set random seed for reproducibility
    torch.manual_seed(args.seed)

    print(
        f"[INFO] Starting BoTorch optimization with {args.trials} trials, seed {args.seed}"
    )

    # Generate bounds for parameters (all between 0 and 1)
    bounds = torch.stack(
        [
            torch.zeros(len(PARAM_SPACE), device=DEVICE),
            torch.ones(len(PARAM_SPACE), device=DEVICE),
        ]
    )

    # Initialize with random points
    train_x = torch.rand(args.init_points, len(PARAM_SPACE), device=DEVICE)
    train_obj = torch.zeros(args.init_points, 1, device=DEVICE)

    # Evaluate initial points
    for i in range(args.init_points):
        train_obj[i] = trial_objective(train_x[i])

    best_value = train_obj.max().item()
    best_params = None
    best_idx = train_obj.argmax().item()

    # Run optimization loop
    for i in range(args.init_points, args.trials):
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
        new_obj = trial_objective(next_point)

        # Update training data
        train_x = torch.cat([train_x, next_point.unsqueeze(0)])
        train_obj = torch.cat([train_obj, new_obj.unsqueeze(0)])

        # Update best value if needed
        if new_obj > best_value:
            best_value = new_obj.item()
            best_idx = i

    # Convert best parameters back to original space
    best_x = train_x[best_idx]
    best_params = {}
    for i, param_name in enumerate(PARAM_SPACE.keys()):
        idx = min(
            int(best_x[i].item() * len(PARAM_SPACE[param_name])),
            len(PARAM_SPACE[param_name]) - 1,
        )
        best_params[param_name] = PARAM_SPACE[param_name][idx]

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


# --- Entry Point ---
if __name__ == "__main__":
    main()
