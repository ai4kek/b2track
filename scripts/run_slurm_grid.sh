#!/bin/bash
#SBATCH --job-name=b2track_grid
#SBATCH --output=logs/grid_%A_%a.out
#SBATCH --error=logs/grid_%A_%a.err
#SBATCH --array=0-9  # 10 parallel jobs
#SBATCH --time=24:00:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1

# Create logs directory if it doesn't exist
mkdir -p logs

# Load Belle II software
source /cvmfs/belle.cern.ch/tools/b2setup release-09-00-00

# Run grid search optimization
# --slurm: tells the script it's running in Slurm mode
# --max-trials: maximum number of grid points to evaluate
# Each job will evaluate max_trials/n_jobs points from the grid
python run_scipy_grid.py --max-trials 100 --slurm

# Note: The script will:
# 1. Each job evaluates its share of grid points
# 2. Write to its own metrics_worker_XX.csv
# 3. Merge all worker files at the end
