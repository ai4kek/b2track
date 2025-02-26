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
import tracking as trkx
import reconstruction as re
import svd
import cdc
import mdst


class PerfModule(b2.Module):
    """Performance module to extract FoM."""

    def __init__(self):
        super().__init__()

        # add variables if needed here:

    def initialize(self):
        """Create a member to access event info and the MCParticles
        StoreArray
        """
        #: an example object from the datastore (the metadata collection for the event)
        self.eventinfo = Belle2.PyStoreObj("EventMetaData")

        #: an example array from the datastore (the list of MC particles)
        self.particles = Belle2.PyStoreArray("MCParticles")

    def beginRun(self):
        """Called every time a run changes before the actual events in that run
        are processed
        """
        b2.B2INFO("beginRun()")

    def event(self):
        """Print the number of charged particles and the total charge"""
        n_charged = 0
        total_charge = 0
        for particle in self.particles:
            charge = particle.getCharge()
            if charge:
                n_charged += 1
            total_charge += charge

        b2.B2INFO(
            f"Number of charged particles = {n_charged}, "
            f"total charge of event = {total_charge}"
        )

    def endRun(self):
        """Called every time a run changes after the actual events in that run
        were processed
        """
        b2.B2INFO("endRun()")

    def terminate(self):
        """Called once after all the processing is complete"""
        b2.B2INFO("terminate()")


# Create the steering path
main = b2.create_path()

# Add simulated data (RootInput)
main.add_module("RootInput", inputFileName="pg_sim.root")

# Only SVD Reconstruction
# svd.add_svd_reconstruction(main)

# Only CDC Reconstruction
# cdc.add_cdc_reconstruction(main)

# Add full reconstruction
# re.add_reconstruction(path=main)

# Add tracking reconstuction
trkx.add_tracking_reconstruction(
    path=main,
    components=None,
    pruneTracks=False,
    mcTrackFinding=False,
    skipGeometryAdding=False,
)

# FoM/Performance Metrics (Tracking Efficiency, Tracking Purity)
# TODO: Add module to print efficiency and purity metrics as plots
# main.add_module(PerfModule())

# Create the mDST output file
additional_br = []
outFile = "pg_track.root"
mdst.add_mdst_output(
    path=main,
    mc=True,
    filename=outFile,
    additionalBranches=additional_br,
    dataDescription=None,
)

# Modules and Paths
b2.print_params(
    "ToCDCCKR", print_values=True, shared_lib_path=None
)  # print module parameters
b2.print_path(
    main, defaults=False, description=False, indentation=0, title=True
)  # prints modules in the given path
b2.process(main)
print(b2.statistics)
