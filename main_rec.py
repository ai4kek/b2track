#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

import basf2 as b2
import cdc
import csv
import generators as ge
import mdst
import reconstruction as re
import simulation as si
import svd
import tracking as trkx
from ROOT import Belle2


def save_params_to_csv(
    module, print_values=True, shared_lib_path=None, filename="parameters.csv"
):
    """
    This function saves parameter information to a CSV file.

    Parameters:
      module: The module to retrieve parameter information from
      filename: Name of the output CSV file (default: 'parameters.csv')
      print_values: If True, saves the current parameter values as well
      shared_lib_path: Path of the shared library from which the module was loaded
    """

    # Gather output data in table
    output = []
    if print_values:
        headers = ["Parameter", "Type", "Default", "Current", "Steering", "Description"]
    else:
        headers = ["Parameter", "Type", "Default", "Description"]

    output.append(headers)

    has_forced_params = False
    paramList = module.available_params()

    for paramItem in paramList:
        defaultStr = str(paramItem.default)
        valueStr = str(paramItem.values)
        forceString = ""
        if paramItem.forceInSteering:
            forceString = "*"
            has_forced_params = True
            defaultStr = ""  # Required parameters don’t have default values

        if print_values:
            row = [
                forceString + paramItem.name,
                paramItem.type,
                defaultStr,
                valueStr,
                paramItem.setInSteering,
                paramItem.description,
            ]
        else:
            row = [
                forceString + paramItem.name,
                paramItem.type,
                defaultStr,
                paramItem.description,
            ]

        output.append(row)

    # Save to CSV file
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(output)

    print(f"[ADAK] {module.name()} parameters saved to {filename}...")


# Create the steering path
main = b2.Path()

# TODO: Set debug_level to 20-29 (To debug CKFToCDCFindlet)
# b2.set_log_level(level=29)

# Add simulated data (RootInput): 'mixed', 'charged', and 'mu+mu-' samples
main.add_module("RootInput", inputFileName="mixed_sim.root")

# Add SVD Reconstruction
# svd.add_svd_reconstruction(main)

# Add CDC Reconstruction
# cdc.add_cdc_reconstruction(main)

# Add full reconstruction
# re.add_reconstruction(path=main)

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
    "filter": "size",
    "pathFilter": "arc_length",
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

b2.set_module_parameters(main, name="ToCDCCKF", type=None, recursive=True, **params)

# Handle ToCDCCKF module
for module in main.modules():
    if module.name() == "ToCDCCKF":
        print(f"[ADAK] The {module} exists in the Path...")
        # module.param("maximalLayerJump", 6)  # change a parameter
        # b2.print_params(module, print_values=True) # print prameters
        # save_params_to_csv(module, print_values=True)  # save parameters


# Print ToCDCCKF prameters
b2.print_params(b2.register_module("ToCDCCKF"), print_values=True)

# Save ToCDCCKF prameters (hacked version of b2.print_params)
save_params_to_csv(b2.register_module("ToCDCCKF"), print_values=True)

# Create the mDST output file
additional_br = []
outFile = "mixed_reco.root"
mdst.add_mdst_output(
    path=main,
    mc=True,
    filename=outFile,
    additionalBranches=additional_br,
    dataDescription=None,
)

# Print modules in path
# b2.print_path(main)

b2.process(main)
# print(b2.statistics)
