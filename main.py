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
import generators as ge
import mdst
import reconstruction as re
import simulation as si
import svd
import tracking as trkx
from ROOT import Belle2

# Create the steering path
main = b2.Path()

# TODO: Set debug_level to 20-29 (To debug CKFToCDCFindlet)
# b2.set_log_level(level=29)

# Add simulated data (RootInput): "mixed", "charged" generic states
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

# TODO: Add SVD, ToCDCCKF


# TODO (DONE): Change ToCDCCKF parameters
params = {
    "maximalDeltaPhi": 0.4,  # Maximal distance in phi between wires for Z=0 plane
    "maximalLayerJump": 6,  # Maximal jump over N layers
    "maximalLayerJumpBackwardSeed": 3,  # Maximal jump over N layers
    "minimalPtRequirement": 0.0,  # Minimal Pt requirement for the input tracks
}

b2.set_module_parameters(main, name="ToCDCCKF", type=None, recursive=True, **params)

# TODO (DONE): Print module parameters
for module in main.modules():
    if module.name() == "ToCDCCKF":
        # module.param("maximalLayerJump", 6)  # change a parameter
        b2.print_params(module, print_values=True, shared_lib_path=None)

# Create the mDST output file
additional_br = []
outFile = "mdst_reco.root"
mdst.add_mdst_output(
    path=main,
    mc=True,
    filename=outFile,
    additionalBranches=additional_br,
    dataDescription=None,
)

# Print modules in path
b2.print_path(main)

b2.process(main)
print(b2.statistics)
