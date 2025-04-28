#!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Load Belle II software
source /cvmfs/belle.cern.ch/tools/b2setup release-09-00-00

# Run grid search with local workers
# --workers: number of CPU cores to use
# --max-trials: maximum number of grid points to evaluate
python run_scipy_grid.py --max-trials 100 --workers $(nproc) 2>&1 | tee logs/grid_local.log
