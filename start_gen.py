#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################


import basf2
import generators as ge

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

# Save all dataobjects
main.add_module("RootOutput", outputFileName=f"dataset/{finalstate}_gen.root")

# Print modules in path
# basf2.print_path(main)

# Run event loop
basf2.process(main)
print(basf2.statistics)
