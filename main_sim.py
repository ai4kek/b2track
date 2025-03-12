#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

import basf2 as b2
import generators as ge
import simulation as si
import mdst

# Create the steering path
main = b2.Path()

# Set EventInfoSetter
main.add_module("EventInfoSetter", evtNumList=[10], expList=[0], runList=[0])

# Generate generic events (finalstate="mixed" (B0B0bar), "charged" (B+B-))
final_state = "mixed"
ge.add_evtgen_generator(
    path=main,
    finalstate=final_state,
    signaldecfile=None,
)

# Add simulation
si.add_simulation(path=main)

# Save output
main.add_module("RootOutput", outputFileName=f"{final_state}_sim.root")

# Print modules in path
# b2.print_path(main)

b2.process(main)
print(b2.statistics)
