#!/bin/bash

# source basf2 release
source /cvmfs/belle.cern.ch/tools/b2setup release-08-03-00

# Note: to pass args to script, add -- before an argparse flag

echo "Job started on $(date)"

# run generator
# basf2 start_gen.py 2>&1 | tee "dataset/start_gen.log"
# echo "start_gen.py script executed successfully..."

# run simulation
# basf2 start_mcri.py 2>&1 | tee "dataset/start_mcri.log"
# echo "start_mcri.py script executed successfully..."

# run reconstruction
basf2 start_rec.py 2>&1 | tee "dataset/start_rec.log"
echo "start_rec.py script executed successfully..."

echo "Job finished on $(date)"
