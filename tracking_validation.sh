#!/bin/bash

# source basf2 release
source /cvmfs/belle.cern.ch/tools/b2setup release-08-03-00


# output dir
mkdir -p validation

# sample name
sample=mixed

# generate ntuples from mDST
echo "generating ntuples from mDST..."
basf2 tracking_performance.py -- -p "validation/$sample" -i "dataset/${sample}_mdst.root"
echo "tracking_performance.py script executed successfully..."

# generate validation metrics
echo "generating validation metrics..."
basf2 tracking_validation.py -- -f1 "validation/${sample}_ntuple.root" -p1 "$sample"
echo "tracking_validation.py script executed successfully..."
