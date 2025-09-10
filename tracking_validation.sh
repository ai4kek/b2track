#!/bin/bash

# source basf2 release (release-08-03-00, release-09-00-03)
source /cvmfs/belle.cern.ch/tools/b2setup release-08-03-00


# default output dir is 'validation/'


# sample name
output_prefix=mixed_hpo

# generate ntuples from mDST > ./validation/mixed_ntuple.root
echo "generating ntuples from mDST..."
basf2 tracking_performance.py -- -p "$output_prefix" -i "dataset/mixed_rec.root" 2>&1 | tee "validation/${output_prefix}.log"
echo "tracking_performance.py script executed successfully..."

# generate validation metrics > ./validation/mixed_hist.root
echo "generating validation metrics..."
basf2 tracking_validation.py -- -p1 "validation/$output_prefix" -f1 "validation/${output_prefix}_ntuple.root"
echo "tracking_validation.py script executed successfully..."
