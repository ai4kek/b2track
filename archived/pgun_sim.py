#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

# Run Script: basf2 pg_sim.py > pg_sim.log 2>&1          # OR
# Run Script: basf2 pg_sim.py 2>&1 | tee pg_sim.log

# flake8: noqa: F401
# ruff: noqa: F401

import basf2 as b2
import generators as ge
import mdst
import reconstruction as re
import simulation as si
from basf2 import (
    LogLevel,
    create_path,
    print_params,
    process,
    register_module,
    set_log_level,
    set_random_seed,
    statistics,
)

# Suppress messages and warnings during processing
set_log_level(LogLevel.WARNING)

# Random seed for particle generation
set_random_seed(123)

# Common PDG Codes
# e- (11) e+ (-11), mu-(13), mu+(-13)
# pi-(-211), pi+(211)
# p (2212), pbar (-2212), n (2112), nbar (-2112)

# ParticleGun generator
pg_gun = b2.register_module("ParticleGun")
pg_gun.param("pdgCodes", [-13, 13])
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
eventinfosetter.param({"evtNumList": [10], "expList": [0], "runList": [0]})

# Show progress of processing
progress = register_module("Progress")

# Load parameters
gearbox = register_module("Gearbox")

# Create geometry
geometry = register_module("Geometry")

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

# Detector Simulation (also loads Gearbox, Geometry, etc.)
si.add_simulation(path=main)

# Create the mDST output file
main.add_module("RootOutput", outputFileName="pg_sim.root")  # save everything
# mdst.add_mdst_output(path=main, filename="mdst_sim.root")  # save subset of above

# Print Modules
# b2.print_path(main)

# Process the steering path
b2.process(path=main)

# Print out statistics about the modules execution
print(b2.statistics)
