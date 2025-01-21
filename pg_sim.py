#!/usr/bin/env python3

# Run Script: `basf2 pg_sim.py > pg_sim.log 2>&1`          # OR
# Run Script: `basf2 pg_sim.py 2>&1 | tee pg_sim.log`


import basf2 as b2
import generators as ge
import simulation as si
import reconstruction as re
import mdst

from basf2 import (
    set_log_level,
    register_module,
    process,
    LogLevel,
    set_random_seed,
    print_params,
    create_path,
    statistics,
)

# Suppress messages and warnings during processing
set_log_level(LogLevel.WARNING)

# Random seed for particle generation
set_random_seed(123)

# ParticleGun generator
pg_gun = b2.register_module("ParticleGun")
pg_gun.param("pdgCodes", [-11, 11])
pg_gun.param("nTracks", 10)
pg_gun.param("varyNTracks", False)
pg_gun.param("momentumGeneration", "uniform")
pg_gun.param("momentumParams", [0.05, 3])
pg_gun.param("thetaGeneration", "uniform")
pg_gun.param("thetaParams", [17, 150])
pg_gun.param("phiGeneration", "uniform")
pg_gun.param("phiParams", [0, 360])
pg_gun.param("vertexGeneration", "fixed")
pg_gun.param("xVertexParams", [0])
pg_gun.param("yVertexParams", [0])
pg_gun.param("zVertexParams", [0])
pg_gun.param("independentVertices", False)

# Print the parameters of the particle gun
print_params(pg_gun)

# ============================================================================

# Create Event information
eventinfosetter = register_module("EventInfoSetter")
eventinfosetter.param({"evtNumList": [10], "runList": [1]})

# Show progress of processing
progress = register_module("Progress")

# Load parameters
gearbox = register_module("Gearbox")

# Create geometry
geometry = register_module("Geometry")

# Save output of generator
output = register_module("RootOutput")
output.param("outputFileName", "pg_sim.root")

# Print MC particle info per event
mcparticleprinter = register_module("PrintMCParticles")
mcparticleprinter.logging.log_level = LogLevel.INFO

# ============================================================================

# Do the simulation
main = b2.create_path()
main.add_module(eventinfosetter)
main.add_module(progress)
main.add_module(pg_gun)
main.add_module(mcparticleprinter)

# Detector Simulation
si.add_simulation(path=main)

# Create the mDST output file
main.add_module(output)

# Process the steering path
b2.process(path=main)

# Print out statistics about the modules execution
print(b2.statistics)

# Print Modules
b2.print_path(main)
