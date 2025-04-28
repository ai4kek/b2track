#!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p logs

# Load Belle II software
source /cvmfs/belle.cern.ch/tools/b2setup release-09-00-00

# Run Ray Tune optimization with local workers
# --workers: number of CPU cores to use
# --trials: total number of trials to run
# --seed: random seed for reproducibility
python run_raytune.py --trials 100 --workers $(nproc) --seed 42 2>&1 | tee logs/raytune_local.log
