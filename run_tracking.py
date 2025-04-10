#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

import basf2
from ROOT import Belle2
import mdst
import tracking as trkx
import json
from src.tracking_metrics import TrackMetrics as TrackingMetrics

# Reproducibility
basf2.set_random_seed(12345)

# Steering Path
main = basf2.Path()

final_state = "mixed"
main.add_module("RootInput", inputFileName=f"dataset/{final_state}_sim.root")

# Tracking reconstruction
trkx.add_tracking_reconstruction(
    path=main,
    components=None,
    pruneTracks=False,
    mcTrackFinding=False,
    skipGeometryAdding=False,
)

# Load ToCDCCKF parameter set
with open("current_params.json", "r") as f:
    params = json.load(f)

# Inject parameters into ToCDCCKF
basf2.set_module_parameters(main, name="ToCDCCKF", recursive=True, **params)

# Calculate tracking metrics
main.add_module(
    TrackingMetrics(params=params, finalstate=final_state, filename="track_metrics.csv")
)

# Add mDST output (not required for search)
# mdst.add_mdst_output(main, mc=True, filename=f"{final_state}_rec.root")

basf2.process(main)
print(basf2.statistics)
