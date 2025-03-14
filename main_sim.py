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

# Create Path
main = b2.Path()

# Set EventInfoSetter
main.add_module("EventInfoSetter", evtNumList=[1000], expList=[0], runList=[0])

# Sample ("mixed" (BBbar), "charged" (B+B-), "mu+mu-", "tau+tau-")
final_state = "mu+mu-"

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
bkg_files = bkg.get_background_files(
    folder=None, output_file_info=True  # if None, it looks from BELLE2_BACKGROUND_DIR
)

# Add simulation
si.add_simulation(
    path=main,
    components=None,
    bkgfiles=None,  # to add backgrond set bkgfiles=bkg_files
    bkgOverlay=True,
)

# Save output
main.add_module("RootOutput", outputFileName=f"{final_state}_sim.root")

# Print modules in path
# b2.print_path(main)

b2.process(main)
print(b2.statistics)
