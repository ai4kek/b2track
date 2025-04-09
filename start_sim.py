#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

import background
import basf2
import generators as ge
import mdst
import simulation as si
import logging

# TODO: How to prepend a globaltag? (see Section 5.4 of basf2 docs)
# TODO: How to add background to simulation? (see Section 9. of basf2 docs)
# TODO: How to visualize wire efficiency map of CDC for an experiment?
# TODO: How to switch on-off some parts of the CDC?

# Reproducibility
basf2.set_random_seed(12345)

# Steering Path
main = basf2.Path()

# Set expList=[0] or [12] or custom, need a specific globaltag/payload.
# For run-independent Monte Carlo simulation set runList=[0] below.
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
# bkg_files = background.get_background_files(folder=bkg_dir, output_file_info=True)

# Add simulation
si.add_simulation(
    path=main,
    components=None,
    bkgfiles=None,  # to add backgrond set bkgfiles=bkg_files
    bkgOverlay=True,
)

# Save output
main.add_module("RootOutput", outputFileName=f"dataset/{final_state}_sim.root")

# Print modules in path
# basf2.print_path(main)

# Run event loop
basf2.process(main)
print(basf2.statistics)
