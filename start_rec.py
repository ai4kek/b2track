#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

import basf2
import mdst
import tracking

# Reproducibility
basf2.set_random_seed(12345)

# Steering Path
main = basf2.Path()

# Add simulated data: 'mixed', 'charged', and 'mu+mu-' samples
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

# Select parameters for ToCDCCKF
params = {
    "maximalDeltaPhi": 0.4,  # Maximal distance in phi between wires for Z=0 plane
    "maximalLayerJump": 4,  # Maximal jump over N layers
    "minimalPtRequirement": 0.0,  # Minimal Pt requirement for the input tracks
    "pathMaximalCandidatesInFlight": 3,  # ???
    "stateMaximalHitCandidates": 4,  # ???
}

# Inject parameters into ToCDCCKF
# basf2.set_module_parameters(main, name="ToCDCCKF", type=None, recursive=True, **params)

# Handle ToCDCCKF module
for module in main.modules():
    if module.name() == "ToCDCCKF":
        print(f"[ADAK] The {module} exists in the Path...")
        # module.param("maximalLayerJump", 6)  # change a parameter
        # basf2.print_params(module, print_values=True) # print prameters
        # save_params_to_csv(module, print_values=True)  # save parameters


# Print ToCDCCKF prameters
# basf2.print_params(basf2.register_module("ToCDCCKF"), print_values=True)

# Save ToCDCCKF prameters (hacked version of basf2.print_params)
# save_params_to_csv(basf2.register_module("ToCDCCKF"), print_values=True)

# Save mDST dataobjects
additional_br = [
    "RecoTracks",
    "RecoTracksToMCParticles",
    "CDCSimHits",
    "CDCHits",
    "SVDSimHits",
    "SVDClusters",
]

mdst.add_mdst_output(
    path=main,
    mc=True,
    filename=f"dataset/{finalstate}_mdst.root",
    additionalBranches=additional_br,
)

# Save all dataobjects
# main.add_module("RootOutput", outputFileName=f"dataset/{finalstate}_reco.root")

# Print modules in path
# basf2.print_path(main)

# Run event loop
basf2.process(main)
# print(basf2.statistics)
