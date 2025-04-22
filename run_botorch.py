"""
BoTorch Optimization for Belle II Tracking Parameters

Uses Gaussian Process-based Bayesian optimization to find optimal
tracking parameters for maximizing efficiency and purity (F1 score).
Logs trials to metrics.csv and supports multiprocessing.

Run:
    python run_botorch_optimization.py
"""

import time
import json
import subprocess
import csv
import torch
from pathlib import Path
from botorch import fitters
from botorch.models import SingleTaskGP
from botorch.optim import optimize_acqf
from botorch.acquisition import ExpectedImprovement
from torch import optim
from torch import Tensor
from typing import List

# --- Configuration ---
PARAM_SPACE = {
    "maximalDeltaPhi": [0.2, 0.3, 0.4],
    "maximalLayerJump": [2, 4, 6],
    "minimalPtRequirement": [0.0, 0.1],
    "pathMaximalCandidatesInFlight": [2, 3],
    "stateMaximalHitCandidates": [3, 4],
}
PARAM_KEYS = list(PARAM_SPACE.keys())
METRICS_PATH = Path("metrics.csv")
NUM_TRIALS = 10  # Define the number of trials


# --- Setup CSV ---
def init_metrics_csv():
    if not METRICS_PATH.exists():
        with METRICS_PATH.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["trial"]
                + PARAM_KEYS
                + ["efficiency", "purity", "f1_score", "execution_time"]
            )


# --- Run Tracking ---
def run_tracking_with_params(
    params: dict, trial_number: int
) -> tuple[float, float, float, float]:
    with open("params.json", "w") as f:
        json.dump(params, f, indent=2)

    start_time = time.time()
    try:
        subprocess.run(["basf2", "run_tracking_svd.py"], check=True)
    except subprocess.CalledProcessError:
        print(f"[ERROR] Trial {trial_number} failed during basf2 execution.")
        return 0.0, 0.0, 0.0, 0.0

    elapsed = round(time.time() - start_time, 2)

    try:
        with METRICS_PATH.open(newline="") as f:
            rows = list(csv.DictReader(f))
            last = rows[-1]
            eff = float(last["efficiency"])
            pur = float(last["purity"])
            f1 = 2 * eff * pur / (eff + pur + 1e-8)
            return eff, pur, f1, elapsed
    except Exception as e:
        print(f"[ERROR] Trial {trial_number} could not parse metrics: {e}")
        return 0.0, 0.0, 0.0, elapsed


# --- Objective Function ---
def objective(params: List[float]) -> float:
    """
    This is the objective function that evaluates a set of parameters and
    returns the F1 score, which will be maximized.
    """
    param_dict = {PARAM_KEYS[i]: params[i] for i in range(len(PARAM_KEYS))}
    trial_number = len(param_history)
    eff, pur, f1, elapsed = run_tracking_with_params(param_dict, trial_number)

    with open(METRICS_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [trial_number]
            + [param_dict[k] for k in PARAM_KEYS]
            + [eff, pur, f1, elapsed]
        )

    return -f1  # Negative because we want to maximize F1 score


# --- BoTorch Optimization Setup ---
def optimize_botorch():
    # Define the initial design (random parameter combinations)
    initial_params = torch.rand(NUM_TRIALS, len(PARAM_SPACE))  # [0, 1] scaled
    # Map the random params back to the search space
    scaled_params = initial_params * torch.tensor(
        [max(v) for v in PARAM_SPACE.values()]
    )

    # Use a Gaussian process to model the objective function
    gp = SingleTaskGP(
        initial_params,
        torch.tensor([objective(p) for p in scaled_params.tolist()]).view(-1, 1),
    )

    # Acquisition function (EI)
    EI = ExpectedImprovement(gp, best_f=torch.tensor([0.0]))

    # Optimization loop
    for trial in range(NUM_TRIALS):
        # Optimize acquisition function to get next candidate
        candidate, _ = optimize_acqf(
            EI,
            bounds=torch.tensor([[0.0] * len(PARAM_SPACE), [1.0] * len(PARAM_SPACE)]),
            q=1,
            num_restarts=10,
            raw_samples=100,
        )

        # Convert the candidate back to the parameter scale
        candidate_params = {
            PARAM_KEYS[i]: candidate[0, i].item() for i in range(len(PARAM_KEYS))
        }

        # Evaluate the objective with the current candidate
        objective(candidate_params)

        # Update the model with the new data point
        new_data = torch.tensor([objective(candidate_params)]).view(-1, 1)
        gp = SingleTaskGP(torch.cat([gp.X, candidate]), torch.cat([gp.Y, new_data]))

    print("\n✅ Optimization complete.")


# --- Entry Point ---
if __name__ == "__main__":
    print("🚀 Starting BoTorch optimization...\n")
    init_metrics_csv()

    optimize_botorch()
