#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

"""
Run-independent (MC16ri) | Run-dependent (MC16rd)
- simulated background   | - background overlay from data
- exp 0 = nominal lumi   | - realistic detector conditions
- exp 1003 = pre-LS1     | - produced with release-08-02 (Run 1)
- exp 1004 = pre-LS2     | - produced with release-08-03 (Run 2)
"""

import background
import basf2
import generators as ge
import simulation as si

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
finalstate = "mixed"

# Add EvtGen generator
if finalstate in ["mixed", "charged"]:
    ge.add_evtgen_generator(
        path=main,
        finalstate=finalstate,
        signaldecfile=None,
    )
# Add KKMC generator
elif finalstate in ["mu+mu-", "tau+tau-"]:
    ge.add_kkmc_generator(
        path=main,
        finalstate=finalstate,
        signalconfigfile="",
    )
else:
    raise ValueError(f"Unknown finalstate: {finalstate}.")

# Add background
bkg_files = background.get_background_files(
    folder=None,  # None >> BELLE2_BACKGROUND_DIR, or set otherwise
    output_file_info=True,
)

# Add simulation
si.add_simulation(
    path=main,
    components=None,
    bkgfiles=bkg_files,  # to add backgrond set bkgfiles=bkg_files
    bkgOverlay=True,
)

# Save all dataobjects
main.add_module("RootOutput", outputFileName=f"dataset/{finalstate}_sim.root")

# Print modules in path
# basf2.print_path(main)

# Run event loop
basf2.process(main)
print(basf2.statistics)
