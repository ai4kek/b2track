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

# TODO: How to prepend a globaltag? (see Section 5.4 of basf2 docs)
# TODO: How to add background to simulation? (see Section 9. of basf2 docs)
# TODO: How to add KKMC for dimuons sample? (see Section 13. of basf2 docs)

# Create Path
main = b2.Path()

# Set expList=[0], or custom [need a specific globaltag] for specific geometry.
# For run-independent Monte Carlo simulation set runList=[0] below.
main.add_module("EventInfoSetter", evtNumList=[1000], expList=[0], runList=[0])

# MC sample: 'mixed' (BBbar), 'charged' (B+B-), 'mu+mu-' (dimuon), 'tau+tau-'
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
bkg_dir = None  # add path to use a specific background folder, 'None' use defalut
bkg_files = bkg.get_background_files(
    folder=None, output_file_info=True  # default Bkg at BELLE2_BACKGROUND_DIR
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
