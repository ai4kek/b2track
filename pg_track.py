#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

import basf2 as b2
import cdc
import generators as ge
import mdst
import reconstruction as re
import simulation as si
import svd
import tracking as trkx
from ROOT import Belle2


# Maybe subclassing TrackingPerformanceEvalutionModule works?
class PerfFoM(b2.Module):
    """The basf2 module to extract performance FoM."""

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


##########################################################################

# Create the steering path
main = b2.Path()

# TODO: Set debug_level to 20-29 (To debug CKFToCDCFindlet)
# b2.set_log_level(level=29)

# Add simulated data (RootInput)
main.add_module("RootInput", inputFileName="mdst_sim.root")

# Add SVD Reconstruction
# svd.add_svd_reconstruction(main)

# Add CDC Reconstruction
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

# TODO: Change some parameters of the ToCDCCKF (Will use kwargs to give new params)
params = {
    "maximalDeltaPhi": 0.4,  # Maximal distance in phi between wires for Z=0 plane
    "maximalLayerJump": 6,  # Maximal jump over N layers
    "maximalLayerJumpBackwardSeed": 3,  # Maximal jump over N layers
    "minimalPtRequirement": 0.0,  # Minimal Pt requirement for the input tracks
}

b2.set_module_parameters(main, name="ToCDCCKF", type=None, recursive=True, **params)

# TODO (DONE): Print module parameters
for module in main.modules():
    if module.name() == "ToCDCCKF":
        # module.param("maximalLayerJump", 6)  # change a parameter
        b2.print_params(module, print_values=True, shared_lib_path=None)

# TODO: Add FoM module to get plots
# main.add_module(PerfFoM())

# Create the mDST output file
additional_br = []
outFile = "mdst_track.root"

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
