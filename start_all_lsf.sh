#!/bin/bash

#BSUB -J "sim"                        # Job name, for job array "sim[1-10]"
#BSUB -P aakram                       # Account name (project ID)
#BSUB -G b2_belle2                    # Group for accounting purposes
#BSUB -n 8                            # Number of cores per job
#BSUB -R "span[hosts=1]"              # Request nodes
#BSUB -q l                            # Submit to queue 's' (short jobs < 3h)
#BSUB -R "rusage[mem=4096]"           # Reserves 4 GB per slot
#BSUB -M 4096                         # MEMLIMIT=4096 for 's' and 'l' queue, killed on overuse    
#BSUB -o logs/sim_%J.out              # Standard output file (%J is job ID, %I is array index)
#BSUB -e logs/sim_%J.err              # Standard error file
#BSUB -u adeel.akram@physics.uu.se    # Email address for notifications
#BSUB -B                              # Send email at job start
#BSUB -N                              # Send email at job completion

echo "Running job $LSB_JOBID on $(hostname)"
echo "Running job index: $LSB_JOBINDEX"



mkdir -p logs
source /cvmfs/belle.cern.ch/tools/b2setup release-08-03-00

echo "Job started on $(date)"

# run generator
basf2 start_gen.py > "logs/start_gen.log" 2>&1
echo "start_gen.py script executed successfully..."

# run simulation
basf2 start_mcri.py > "logs/start_mcri.log" 2>&1
echo "start_mcri.py script executed successfully..."

# run reconstruction
basf2 start_rec.py > "logs/start_rec.log" 2>&1
echo "start_rec.py script executed successfully..."

echo "Job finished on $(date)"
