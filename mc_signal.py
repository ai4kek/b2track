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
import reconstruction as re
import mdst

# Create the steering path
main = b2.Path()

# Define number of events and experiment number
main.add_module("EventInfoSetter", evtNumList=[10], expList=[0], runList=[0])

# Generate signal events (finalstate='signal', signaldecfile=xyz.dec)
ge.add_evtgen_generator(
    path=main, finalstate="signal", signaldecfile=b2.find_file("signal_B0_Jpsi_KS0.dec")
)

# Simulate the detector response and the L1 trigger
si.add_simulation(path=main)
# or si.add_simulation(main, components) to simulate a selection of detectors and trigger

# Reconstruct the objects
re.add_reconstruction(path=main)
# or re.add_reconstruction(main, components) to run the reconstruction of a selection of detectors

# Create the mDST output file
mdst.add_mdst_output(path=main, filename="mdst_signal_B0_Jpsi_KS0.root")

# Print modules in path
# b2.print_path(main)

# Process the steering path
b2.process(path=main)

# Modules execution statistics
print(b2.statistics)
