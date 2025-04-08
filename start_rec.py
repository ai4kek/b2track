#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

import basf2 as b2
import mdst
import tracking as trkx

# Steering path
main = b2.Path()

# Add simulated data: 'mixed', 'charged', and 'mu+mu-' samples
final_state = "mixed"
main.add_module("RootInput", inputFileName=f"dataset/{final_state}_sim.root")

# Add full tracking reconstuction
trkx.add_tracking_reconstruction(
    path=main,
    components=None,
    pruneTracks=False,
    mcTrackFinding=False,
    skipGeometryAdding=False,
)

# ToCDCCKF parameters
params = {
    "maximalDeltaPhi": 0.4,  # Maximal distance in phi between wires for Z=0 plane
    "maximalLayerJump": 4,  # Maximal jump over N layers
    "minimalPtRequirement": 0.0,  # Minimal Pt requirement for the input tracks
    "pathMaximalCandidatesInFlight": 3,  # ???
    "stateMaximalHitCandidates": 4,  # ???
}

params_1 = {
    # "filter": "size",
    # "pathFilter": "arc_length",
    # "filterParameters": {},
    # "pathFilterParameters": {},
    # "stateBasicFilterParameters": {'maximalHitDistance': 0.15},
    # "stateExtrapolationFilterParameters": {},
    # "stateFinalFilterParameters": {},
    # "statePreFilterParameters": {},
    "exportAllTracks": False,  #
    "exportTracks": True,  #
    "ignoreTracksWithCDChits": True,  #
    "setTakenFlag": True,  #
}

# b2.set_module_parameters(main, name="ToCDCCKF", type=None, recursive=True, **params)

# Handle ToCDCCKF module
for module in main.modules():
    if module.name() == "ToCDCCKF":
        print(f"[ADAK] The {module} exists in the Path...")
        # module.param("maximalLayerJump", 6)  # change a parameter
        # b2.print_params(module, print_values=True) # print prameters
        # save_params_to_csv(module, print_values=True)  # save parameters


# Print ToCDCCKF prameters
# b2.print_params(b2.register_module("ToCDCCKF"), print_values=True)

# Save ToCDCCKF prameters (hacked version of b2.print_params)
# save_params_to_csv(b2.register_module("ToCDCCKF"), print_values=True)

# Create the mDST
additional_br = []
mdst.add_mdst_output(
    path=main,
    mc=True,
    filename=f"dataset/{final_state}_rec.root",
    additionalBranches=additional_br,
    dataDescription=None,
)

# Print modules in path
b2.print_path(main)

# Run event loop
b2.process(main)
print(b2.statistics)
