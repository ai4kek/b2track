#!/bin/bash

# from local cvmfs
source /cvmfs/belle.cern.ch/tools/b2setup release-09-00-00

# run generator
basf2 start_gen.py > "dataset/start_gen.log" 2>&1
echo "start_gen.py script executed successfully..."

# run simulation
basf2 start_sim.py > "dataset/start_sim.log" 2>&1
echo "start_sim.py script executed successfully..."

# run reconstruction
basf2 start_rec.py > "dataset/start_rec.log" 2>&1
echo "start_rec.py script executed successfully..."
