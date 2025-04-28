"""Common configuration for tracking parameter optimization."""

from pathlib import Path

# Parameter space definition
PARAM_SPACE = {
    "maximalDeltaPhi": [0.2, 0.3, 0.4],
    "maximalLayerJump": [2, 4, 6],
    "minimalPtRequirement": [0.0, 0.1],
    "pathMaximalCandidatesInFlight": [2, 3],
    "stateMaximalHitCandidates": [3, 4],
}

# Paths
METRICS_PATH = Path("metrics.csv")
PARAMS_PATH = Path("params.json")

# CSV fields
METRICS_FIELDS = [
    *list(PARAM_SPACE.keys()),
    "efficiency",
    "purity",
    "f1_score",
    "final_state",
    "execution_time",
]

# Tracking command (with -- separator for basf2 argument passing)
TRACKING_CMD = ["basf2", "run_tracking_svd.py", "--"]

# Optimization settings
MAX_TRIALS = 20
RANDOM_SEED = 42
