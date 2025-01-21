#!/usr/bin/env python3

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
main.add_module("RootOutput", outputFileName="pg_reco.root")

# Process the steering path
b2.process(path=main)

# Print out statistics about the modules execution
print(b2.statistics)
