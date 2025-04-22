#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

"""
Optuna Optimization Script for Belle II Tracking Parameters

This script performs intelligent parameter optimization for the ToCDCCKF tracking module
in the Belle II software framework using Optuna. It searches for a combination of 5 
tracking parameters that maximize the F1 score, which is the harmonic mean of tracking 
efficiency and purity.

How It Works:
-------------
- Parameters are sampled using Optuna's TPE (Bayesian) strategy.
- Each parameter set is written to `params.json`.
- `basf2 run_tracking_svd.py` is called, which runs the tracking reconstruction pipeline.
- `TrackingMetrics` in your pipeline saves efficiency and purity to `metrics.csv`.
- This script reads the latest metrics from the CSV and returns a score to Optuna.
- The score being maximized is the F1 score:
  F1 = 2 * (efficiency * purity) / (efficiency + purity)

Requirements:
-------------
- Belle II software environment should be active (`basf2` should be on PATH).
- The `run_tracking_svd.py` script should read parameters from `params.json`.
- The `TrackingMetrics` module should write a `metrics.csv` with `efficiency` and `purity` fields.

Usage:
------
Just run the script:

    python run_optuna.py

To run in parallel using a shared SQLite database (optional):

    1. Create a study:
       optuna create-study --study-name track_optimization \
            --storage sqlite:///optuna_tracking.db --direction maximize

    2. Replace the study definition in this script with:
       study = optuna.load_study(study_name="track_optimization",
                                 storage="sqlite:///optuna_tracking.db")

    3. Launch multiple workers:
       python run_optuna.py
       python run_optuna.py
       ...
"""

import os
import json
import time
import subprocess
import csv
from pathlib import Path
from multiprocessing import Lock, Manager
import optuna
from optuna.samplers import TPESampler
from optuna.storages import RDBStorage

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
SQLITE_PATH = "sqlite:///optuna_study.db"
STUDY_NAME = "tracking_optimization"


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
def objective(trial):
    params = {k: trial.suggest_categorical(k, v) for k, v in PARAM_SPACE.items()}
    trial_number = trial.number
    eff, pur, f1, elapsed = run_tracking_with_params(params, trial_number)

    with LOCK:
        with METRICS_PATH.open("a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [trial_number]
                + [params[k] for k in PARAM_KEYS]
                + [eff, pur, f1, elapsed]
            )

    print(f"[✓] Trial {trial_number} complete — F1: {f1:.4f}")
    return f1


# --- Entry Point ---
if __name__ == "__main__":
    print("🚀 Starting Optuna optimization with SQLite logging...\n")
    init_metrics_csv()

    with Manager() as manager:
        LOCK = manager.Lock()

        # Connect to SQLite DB
        storage = RDBStorage(url=SQLITE_PATH)

        # Choose a Sampler (TPE is default)
        sampler = TPESampler(seed=42)

        study = optuna.create_study(
            direction="maximize",
            study_name=STUDY_NAME,
            storage=storage,
            sampler=sampler,
            load_if_exists=True,
        )
        study.optimize(objective, n_trials=20, n_jobs=os.cpu_count())

    print("\n✅ Optimization complete.")
    print(f"Best trial:\n{study.best_trial}")
    print(f"Score (F1): {study.best_value:.4f}")
    print(f"Params: {study.best_params}")
    print(f"Efficiency: {study.best_trial.user_attrs['efficiency']}")
    print(f"Purity: {study.best_trial.user_attrs['purity']}")

    print(f"\n📊 View results:\n    optuna-dashboard {SQLITE_PATH}")
