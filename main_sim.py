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

# Define number of events and experiment number
main.add_module("EventInfoSetter", evtNumList=[10], expList=[0], runList=[0])

# Generate signal events (finalstate='signal', signaldecfile=xyz.dec)
ge.add_evtgen_generator(
    path=main, finalstate="signal", signaldecfile=b2.find_file("signal_B0_Jpsi_KS0.dec")
)

si.add_simulation(path=main)


# Create the mDST output file
additional_br = []
outFile = "mdst_sim.root"

mdst.add_mdst_output(
    path=main,
    mc=True,
    filename=outFile,
    additionalBranches=additional_br,
    dataDescription=None,
)

# Print modules in the given path
b2.print_path(main, defaults=False, description=False, indentation=0, title=True)

b2.process(main)
# print(b2.statistics)
