#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

import argparse
import json

import basf2
import mdst
import tracking


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run SVD tracking with specified parameters"
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
    parser.add_argument(
        "--finalstate",
        type=str,
        default="mixed",
        help="Final state type (default: %(default)s)",
    )
    # Handle both direct python and basf2 argument passing
    try:
        return parser.parse_args()
    except SystemExit:
        # If parsing fails (when run with python directly), return default values
        return parser.parse_args([])


def main():
    args = parse_args()

    # Reproducibility
    basf2.set_random_seed(12345)

    # Steering Path
    main = basf2.Path()

    # Add simulated data: 'mixed', 'charged', and 'mu+mu-' samples
    main.add_module("RootInput", inputFileName=args.input)

    # Add full tracking reconstuction
    tracking.add_tracking_reconstruction(
        path=main,
        components=None,
        pruneTracks=False,
        mcTrackFinding=False,
        skipGeometryAdding=False,
    )

    # Pass args to ToCDCCKF if provided
    if args.params is not None:

        # Load ToCDCCKF parameters from JSON file
        with open(args.params, "r") as f:
            params = json.load(f)

        # Print loaded parameters
        print(params)

        # Inject parameters into ToCDCCKF
        basf2.set_module_parameters(main, name="ToCDCCKF", recursive=True, **params)

        # Print ToCDCCKF prameters
        basf2.print_params(basf2.register_module("ToCDCCKF"), print_values=True)

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
        filename=f"{args.output}",
        # additionalBranches=additional_br,
    )

    # Save all dataobjects
    # main.add_module("RootOutput", outputFileName=f"{args.output}")

    # Print modules in path
    # basf2.print_path(main)

    # Run event loop
    basf2.process(main)
    # print(basf2.statistics)


if __name__ == "__main__":
    main()
