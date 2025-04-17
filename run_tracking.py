#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

# Intended to run with run_search.py script as a subprocess for different
# trails with specific params. For just tracking, run the start_rec.py.

import basf2
import mdst
import tracking
import json
from src.tracking_metrics import TrackMetrics as TrackingMetrics

# Reproducibility
basf2.set_random_seed(12345)

# Steering Path
main = basf2.Path()

finalstate = "mixed"
main.add_module("RootInput", inputFileName=f"dataset/{finalstate}_sim.root")

# Add full tracking reconstuction
tracking.add_tracking_reconstruction(
    path=main,
    components=None,
    pruneTracks=False,
    mcTrackFinding=False,
    skipGeometryAdding=False,
)

# Load ToCDCCKF parameter set
with open("params.json", "r") as f:
    params = json.load(f)

# Inject parameters into ToCDCCKF
basf2.set_module_parameters(main, name="ToCDCCKF", recursive=True, **params)

# Calculate tracking metrics
metrics = TrackingMetrics(params, finalstate, filename="metrics.csv")
main.add_module(metrics)

# Save mDST dataobjects (not required for search)
# mdst.add_mdst_output(main, mc=True, filename=f"{dataset/{final_state}_mds.root")

# Save all dataobjects (not required for search)
# main.add_module("RootOutput", outputFileName=f"dataset/{final_state}_reco.root")

basf2.process(main)
# print(basf2.statistics)
