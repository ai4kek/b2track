#!/bin/bash

# from local cvmfs
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
