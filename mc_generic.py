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
import mdst
import reconstruction as re
import simulation as si

# Create the steering path
main = b2.Path()

# Define number of events and experiment number
main.add_module("EventInfoSetter", evtNumList=[10], expList=[0], runList=[0])

# Generate generic events (finalstate="mixed" (B0B0bar), "charged" (B+B-))
final_state = "mixed"
ge.add_evtgen_generator(
    path=main,
    finalstate=final_state,
    signaldecfile=None,
)

# Simulate the detector response and the L1 trigger
si.add_simulation(path=main)
# or si.add_simulation(main, components) to simulate a selection of detectors and trigger

# Reconstruct the objects
re.add_reconstruction(path=main)
# or re.add_reconstruction(main, components) to run the reconstruction of a selection of detectors

# Create the mDST output file
mdst.add_mdst_output(path=main, filename=f"mdst_{final_state}.root")

# Print modules in path
# b2.print_path(main)

# Process the steering path
b2.process(path=main)

# Modules execution statistics
print(b2.statistics)
