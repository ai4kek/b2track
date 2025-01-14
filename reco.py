#!/usr/bin/env python3

import basf2 as b2
import generators as ge
import simulation as si
import reconstruction as re
import mdst

# Create the steering path
main = b2.Path()

# create path
main = b2.create_path()

# add simulated data (ParticleGun)
input_file = "pg_output.root"
main.add_module("RootInput", inputFileName=input_file)

# OR,
rootinput = b2.register_module("RootInput")
input = (
    "/ghi/fs01/belle2/bdata/group/detector/CDC/unpacked/exp00/cr.cdc.0000.001733.root"
)
rootinput.param("inputFileName", input)
main.add_module(rootinput)

# Reconstruct the objects
# re.add_reconstruction(path=main)
# or re.add_reconstruction(main, components) to run the reconstruction of a selection of detectors


# Create the mDST output file
output_filename = "pg_reco.root"
main.add_module("RootOutput", outputFileName=output_filename)

root_output = b2.register_module("RootOutput")
root_output.param("outputFileName", output_filename)


# Process the steering path
b2.process(path=main)

# Finally, print out some statistics about the modules execution
print(b2.statistics)
