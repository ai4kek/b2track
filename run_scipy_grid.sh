#!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Load Belle II software
source /cvmfs/belle.cern.ch/tools/b2setup release-09-00-00

# Default values
MAX_TRIALS=20
TOL=0.0001
WORKERS=$(nproc)
SEED=42

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --max-trials)
            MAX_TRIALS="$2"
            shift 2
            ;;
        --tol)
            TOL="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --seed)
            SEED="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
            exit 1
            ;;
    esac
done

# Run differential evolution optimization with local workers
# --max-trials: safety limit for number of trials
# --tol: convergence tolerance
# --workers: number of CPU cores to use
# --seed: random seed for reproducibility
python3 run_scipy_grid.py \
    --max-trials "${MAX_TRIALS}" \
    --tol "${TOL}" \
    --workers "${WORKERS}" \
    --seed "${SEED}" \
    2>&1 | tee logs/grid_local.log
