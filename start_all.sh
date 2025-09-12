#!/bin/bash

# source basf2 release (release-08-03-00, release-09-00-03)
source /cvmfs/belle.cern.ch/tools/b2setup release-08-03-00

# Note: to pass args to script, add -- before an argparse flag. For example,
# basf2 start_rec.py -- --input dataset/mixed_sim.root --finalstate mixed
# --outputdir dataset --params best_params.json

echo "Job started on $(date)"

# run generator
# basf2 start_gen.py 2>&1 | tee "dataset/mixed_gen.log"
# echo "start_gen.py script executed successfully..."

# run simulation (mcri, mcrd)
# basf2 start_mcrd.py 2>&1 | tee "dataset/mixed_mcrd.log"
# echo "start_mcrd.py script executed successfully..."

# run reconstruction (mdst, mdst+)
# basf2 start_rec.py -- --input dataset/mixed_mcrd.root --output dataset/mixed_mcrd_mdst.root 2>&1 | tee "dataset/mixed_mcrd_mdst.log"
# basf2 start_rec.py -- --input dataset/mixed_mcrd.root --output dataset/mixed_mcrd_mdst_hpo.root --params best_mcrd.json 2>&1 | tee "dataset/mixed_mcrd_mdst_hpo.log"
# echo "start_rec.py script executed successfully..."

echo "Job finished on $(date)"
