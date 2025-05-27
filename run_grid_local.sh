#!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Load Belle II software
source /cvmfs/belle.cern.ch/tools/b2setup release-08-03-00

# Get the number of available CPU cores
AVAILABLE_CORES=$(nproc)

# Default to using half of the available CPU cores
# This ensures each worker gets a dedicated core by default
DEFAULT_WORKERS=$((AVAILABLE_CORES / 2))
# If only 1 core is available, use 1 worker
[[ $DEFAULT_WORKERS -lt 1 ]] && DEFAULT_WORKERS=1
WORKERS=$DEFAULT_WORKERS

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
            exit 1
            ;;
    esac
done

# Check if requested workers exceed available cores
if [[ $WORKERS -gt $AVAILABLE_CORES ]]; then
    echo "Warning: Requested workers (${WORKERS}) exceed available cores (${AVAILABLE_CORES})."
    echo "Workers will share CPU cores, which may reduce performance."
    
    # Run without CPU affinity restrictions
    USE_TASKSET=0
else
    echo "Each worker will use a dedicated CPU core."
    
    # Use taskset to control CPU affinity
    USE_TASKSET=1
fi

echo "Running grid search with ${WORKERS} workers on $(hostname) (${AVAILABLE_CORES} cores available)"
echo "Job started on $(date)"

# Run grid search with local workers
if [[ $USE_TASKSET -eq 1 ]]; then
    # Use taskset to restrict the process to specific CPU cores
    # This helps ensure each worker gets its own core
    taskset -c 0-$((WORKERS-1)) python3 run_scipy_grid.py --workers "${WORKERS}" 2>&1 | tee logs/grid_local.log
else
    # Run without CPU affinity restrictions
    python3 run_grid.py --workers "${WORKERS}" 2>&1 | tee logs/grid_local.log
fi

echo "Job finished on $(date)"
