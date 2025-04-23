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

# Save all dataobjects
main.add_module("RootOutput", outputFileName=f"dataset/{final_state}_gen.root")

# Print modules in path
# basf2.print_path(main)

# Run event loop
basf2.process(main)
print(basf2.statistics)
