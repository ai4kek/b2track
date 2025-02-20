#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################


# Write a Python script that simulates generic Y(4S) events with beam background
# using EarlyPhase3 geometry (hint: experiment number 1003), reconstruct them,
# and write an output ROOT file containing all the StoreArrays (hint: check
# svd/examples and analysis/examples/tutorials for guidance).


import basf2 as b2
from ROOT import Belle2
import glob
import svd
import simulation as si

# fileout = "my_new_svdex100.root"
fileout = "my_new_svdex10k.root"

bg = glob.glob(
    "/group/belle2/dataprod/BGOverlay/early_phase3/release-08-00-03/overlay/BGx1/set0/*.root"
)

main = b2.create_path()
main.add_module("EventInfoSetter", expList=1003, runList=0, evtNumList=10000)
main.add_module("EvtGenInput")

main.add_module("EventInfoPrinter")
main.add_module("Gearbox")
main.add_module("Geometry")

si.add_simulation(main, bkgfiles=bg)

# Simply run the tracking reconstuction
# from tracking import add_tracking_reconstruction()
# On can enable and disable PXD, SVD and/or CDD


# Only SVD Reconstruction
svd.add_svd_reconstruction(main, createRecoDigits=True)
input_branches = [
    "SVDShaperDigits",
    "SVDRecoDigits",
    "SVDSpacePoints",
    "SVDClusters",
    "SVDEventInfoSim",
]

# Only CDC Reconstruction
# cdc.add_cdc_reconstruction(...)

main.add_module("RootOutput", branchNames=input_branches, outputFileName=fileout)

b2.print_path(main)
b2.process(main)
print(b2.statistics)
