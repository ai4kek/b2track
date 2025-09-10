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

mkdir -p logs
echo "Running job $LSB_JOBID on $(hostname)"
echo "Running job index: $LSB_JOBINDEX"

# source basf2 release
source /cvmfs/belle.cern.ch/tools/b2setup release-08-03-00

# Note: to pass args to script, add -- before an argparse flag. For example,
# basf2 start_rec.py -- --input dataset/mixed_sim.root --finalstate mixed
# --outputdir dataset --params best_params.json

echo "Job started on $(date)"

# run generator
# basf2 start_gen.py 2>&1 | tee "dataset/start_gen.log"
# echo "start_gen.py script executed successfully..."

# run simulation (mcri, mcrd)
# basf2 start_mcri.py 2>&1 | tee "dataset/start_mcri.log"
# echo "start_mcri.py script executed successfully..."

# run reconstruction (mdst, mdst+)
basf2 start_rec.py -- --input dataset/mixed_sim.root --output dataset/mixed_mdst.root 2>&1 | tee "dataset/mixed_mdst.log"
# basf2 start_rec.py -- --input dataset/mixed_sim.root --output dataset/mixed_mdst.root --params best_params.json 2>&1 | tee "dataset/mixed_mdst_hpo.log"

echo "start_rec.py script executed successfully..."

echo "Job finished on $(date)"
