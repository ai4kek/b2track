#!/usr/bin/env python3

# Run Script: `basf2 pg_reco.py > pg_reco.log 2>&1`        # OR
# Run Script: `basf2 pg_reco.py 2>&1 | tee pg_reco.log`


import basf2 as b2
import generators as ge
import simulation as si
import reconstruction as re
import mdst


# Create the steering path
main = b2.create_path()

# add simulated data (ParticleGun)
main.add_module("RootInput", inputFileName="pg_sim.root")

# Reconstruct the objects
re.add_reconstruction(path=main)

# Create the mDST output file
# main.add_module("RootOutput", outputFileName="pg_reco.root")  # save everything
mdst.add_mdst_output(
    path=main, mc=True, filename="pg_reco.root"
)  # save subset of above

# Print Modules
# b2.print_path(main)

# Process the steering path
b2.process(path=main)

# Print out statistics about the modules execution
print(b2.statistics)
