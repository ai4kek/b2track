#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

import background as bkg
import basf2 as b2
import generators as ge
import mdst
import simulation as si
import tracking as trkx

# Reproducibility
b2.set_random_seed(12345)

# Logging
b2.set_log_level(b2.LogLevel.INFO)

# Steering Path
main = b2.Path()

main.add_module("EventInfoSetter", evtNumList=[1000], expList=[0], runList=[0])

# MC sample: 'mixed' (BBbar), 'charged' (B+B-), 'mu+mu-' (dimuon), 'tau+tau-'
final_state = "mixed"

# Add EvtGen generator
if final_state in ["mixed", "charged"]:
    ge.add_evtgen_generator(
        path=main,
        finalstate=final_state,
        signaldecfile=None,
    )
# Add KKMC generator
elif final_state in ["mu+mu-", "tau+tau-"]:
    ge.add_kkmc_generator(
        path=main,
        finalstate=final_state,
        signalconfigfile="",
    )
else:
    raise ValueError(f"Unknown final_state: {final_state}.")

# Add background
# bkg_dir = None  # None (default: BELLE2_BACKGROUND_DIR on KEKCC) or set a path
# bkg_files = bkg.get_background_files(folder=bkg_dir, output_file_info=True)

# Add simulation
si.add_simulation(
    path=main,
    components=None,
    bkgfiles=None,  # to add backgrond set bkgfiles=bkg_files
    bkgOverlay=True,
)


# Add tracking reconstuction
trkx.add_tracking_reconstruction(
    path=main,
    components=None,
    pruneTracks=False,
    mcTrackFinding=False,
    skipGeometryAdding=False,
)

# Create the mDST
additional_br = []
mdst.add_mdst_output(
    path=main,
    mc=True,
    filename=f"dataset/{final_state}_main.root",
    additionalBranches=additional_br,
    dataDescription=None,
)

# Print modules in path
b2.print_path(main)

b2.process(main)
print(b2.statistics)
