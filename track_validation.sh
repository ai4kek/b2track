#!/bin/bash

# init basf2
source /cvmfs/belle.cern.ch/tools/b2setup release-08-03-00

# sample name
sample=mixed

# generate ntuples
echo "generating ntuples..."
basf2 tracking_performance.py -- -p "$sample" -i "dataset/${sample}_mdst.root"
echo "tracking_performance.py script executed successfully..."

# generate validation metrics
echo "generating validation metrics..."
basf2 tracking_validation.py -- -f1 "${sample}/${sample}_ntuple.root" -p1 "$sample"
echo "tracking_validation.py script executed successfully..."
