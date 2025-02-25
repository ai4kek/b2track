#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################


# Write a Python script that simulates generic Y(4S) events with beam background
# using EarlyPhase3 geometry (hint: experiment number 1003), reconstruct them,
# and write an output ROOT file containing all the StoreArrays (hint: check
# svd/examples and analysis/examples/tutorials for guidance).

import basf2 as b2
import generators as ge
import simulation as si
import tracking as trkx
import reconstruction as re
import svd
import cdc
import mdst

# Create the steering path
main = b2.create_path()

# Add simulated data (RootInput)
main.add_module("RootInput", inputFileName="pg_sim.root")

# Only SVD Reconstruction
# svd.add_svd_reconstruction(main)

# Only CDC Reconstruction
# cdc.add_cdc_reconstruction(main)

# Add full reconstruction
# re.add_reconstruction(path=main)


# Add tracking reconstuction
trkx.add_tracking_reconstruction(
    path=main,
    components=None,
    pruneTracks=False,
    mcTrackFinding=False,
    skipGeometryAdding=False,
)

# Create the mDST output file
outFile = "pg_track.root"
# mdst.add_mdst_output(path=main, mc=True, filename="mdst_"+outFile
# )  # save only branches defined in mdst.add_mdst_output()

# OR, Directly add to RootOutput
# TODO: Figure out which branches are needed, only save them rather that everything
output_br = [
    "ECLClusters",
    "ECLClustersToTracksNamedBremsstrahlung",
    "EventLevelClusteringInfo",
    "EventLevelTrackingInfo",
    "EventLevelTriggerTimeInfo",
    "KLMClusters",
    "Kinks",
    "KlIds",
    "PIDLikelihoods",
    "SoftwareTriggerResult",
    "TrackFitResults",
    "Tracks",
    "TRGSummary",
    "V0s",
    "MCParticles",
    "CDCRecoTrack",
]

main.add_module("RootOutput", outputFileName=outFile)  # save everything

b2.print_path(main)
b2.process(main)
print(b2.statistics)
