#!/bin/bash

#BSUB -J "grid[0-9]"                  # Job array with 8 workers
#BSUB -P aakram                       # Account name (project ID)
#BSUB -G b2_belle2                    # Group for accounting purposes
#BSUB -n 1                            # Number of cores per job
#BSUB -R "span[hosts=1]"              # Request nodes
#BSUB -q s                            # Submit to queue 's' (short jobs < 3h)
#BSUB -W 02:55                        # Runtime (hh:mm)
#BSUB -o logs/grid_%J_%I.out          # Standard output file (%J is job ID, %I is array index)
#BSUB -e logs/grid_%J_%I.err          # Standard error file
#BSUB -u adeel.akram@physics.uu.se    # Email address for notifications
#BSUB -B                              # Send email at job start
#BSUB -N                              # Send email at job completion

mkdir -p logs
source /cvmfs/belle.cern.ch/tools/b2setup release-09-00-00

echo "Running grid search job $LSB_JOBID on $(hostname)"
echo "Running job array index: $LSB_JOBINDEX of $LSB_JOBINDEX_END"

echo "Job started on $(date)"

# main grid search command
python3 run_scipy_grid.py --cluster

# test job array limitations with a 2-minute sleep
# echo "Worker ${LSB_JOBINDEX}: Sleeping for 2 minutes..."
# sleep 120  # 2 minutes
# echo "Worker ${LSB_JOBINDEX}: Woke up"

echo "Job finished on $(date)"
