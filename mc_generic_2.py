#!/usr/bin/env python3

import basf2 as b2
import generators as ge
import simulation as si
import reconstruction as re
import mdst

# Create the steering path
# main = b2.Path()
main = b2.create_path()

# Define number of events and experiment number
main.add_module("EventInfoSetter", evtNumList=[10], expList=[0])

# Generate generic events (finalstate='mixed' (B0B0bar), 'charged' (B+B-))
ge.add_evtgen_generator(path=main, finalstate="mixed", signaldecfile=None)

# Simulate the detector response and the L1 trigger
si.add_simulation(path=main)
# or si.add_simulation(main, components) to simulate a selection of detectors and triggr

# Reconstruct the objects
re.add_reconstruction(path=main)
# or re.add_reconstruction(main, components) to run the reconstruction of a selection of detectors

# Remaining Modules
main.add_module("Progress")
main.add_module("Gearbox")
main.add_module("RootOutput", outputFileName="generic_mc_mixed.root")
main.add_module("PrintMCParticles", logLevel=b2.LogLevel.DEBUG, onlyPrimaries=False)


# Process the steering path
b2.process(path=main)

# Finally, print out some statistics about the modules execution
print(b2.statistics)
