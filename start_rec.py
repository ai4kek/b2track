#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

import argparse
import json
import basf2 as b2
import mdst as mdst
import tracking as tr
from src.utils import print_module_params

# run w/ defaults: basf2 start_rec.py 2>&1 | tee "dataset/mixed_rec.log"

def parse_args():
    parser = argparse.ArgumentParser(
        description="Run basf2 Full Tracking Reconstruction"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="dataset/mixed_sim.root",
        help="Input ROOT file path (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dataset/mixed_mdst.root",
        help="Output ROOT file path (default: %(default)s)",
    )
    parser.add_argument(
        "--params",
        type=str,
        default=None,
        help="Path to JSON file with ToCDCCKF parameters (optional)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Reproducibility
    b2.set_random_seed(12345)

    # Steering Path
    main = b2.Path()

    # Add simulated data
    main.add_module("RootInput", inputFileName=args.input)

    # Add full tracking reconstuction
    tr.add_tracking_reconstruction(
        path=main,
        components=None,
        pruneTracks=False,
        mcTrackFinding=False,
        skipGeometryAdding=False,
    )

    # Inject parameters into TFCDC_WireHitPreparer
    # basf2.set_module_parameters(
    #    main, "TFCDC_WireHitPreparer", useSuperLayers=[0,1,2,5,6,7,8])

    # Inject parameters to ToCDCCKF
    if args.params is not None:

        # Load ToCDCCKF parameters from JSON file
        with open(args.params, "r") as f:
            params = json.load(f)

        # Inject parameters into ToCDCCKF
        b2.set_module_parameters(
            main, name="ToCDCCKF", recursive=True, **params)

        # Print new prameters, don't use b2.print_params() rather use this wrapper
        print_module_params(main, "ToCDCCKF")

    # Save mDST dataobjects
    additional_br = [
        "RecoTracks",
        "RecoTracksToMCParticles",
        "CDCSimHits",
        "CDCHits",
        "SVDSimHits",
        "SVDClusters",
    ]

    mdst.add_mdst_output(
        path=main,
        mc=True,
        filename=args.output,
        # additionalBranches=additional_br,
    )

    # Print modules in path
    b2.print_path(main)

    # Run event loop
    b2.process(main)
    # print(b2.statistics)


if __name__ == "__main__":
    main()
