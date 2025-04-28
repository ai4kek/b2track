#!/bin/bash
#SBATCH --job-name=b2track_raytune
#SBATCH --output=logs/raytune_%A_%a.out
#SBATCH --error=logs/raytune_%A_%a.err
#SBATCH --array=0-9  # 10 parallel jobs
#SBATCH --time=24:00:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1

# Create logs directory if it doesn't exist
mkdir -p logs

# Load Belle II software
source /cvmfs/belle.cern.ch/tools/b2setup release-09-00-00

# Run Ray Tune optimization
# --slurm: tells the script it's running in Slurm mode
# --trials: total number of trials across all jobs (e.g., 100 trials = 10 per job)
# --seed: base random seed (each job gets seed + job_id for reproducibility)
python run_raytune.py --trials 100 --slurm --seed 42

# Note: The script will:
# 1. Each job handles trials/n_jobs trials
# 2. Write to its own metrics_worker_XX.csv
# 3. Merge all worker files at the end
