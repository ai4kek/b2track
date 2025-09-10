#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

import argparse

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
        help="Input ROOT file path (default: dataset/mixed_sim.root)",
    )
    parser.add_argument(
        "--finalstate",
        type=str,
        default="mixed",
        help="Final state type (default: mixed)",
    )

    parser.add_argument(
        "--outputdir",
        type=str,
        default="dataset",
        help="Output directory (default: dataset)",
    )
    parser.add_argument(
        "--params",
        type=str,
        default=None,
        help="Path to JSON file with ToCDCCKF parameters (optional)",
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

    # Pass args to ToCDCCKF if --params is provided by the user.
    if args.params is not None:

        # Load ToCDCCKF parameters from JSON file
        with open(args.params, "r") as f:
            params = json.load(f)

        # Print parameters
        print(params)

        # Inject parameters into ToCDCCKF
        basf2.set_module_parameters(main, name="ToCDCCKF", recursive=True, **params)

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
        filename=f"{args.outputdir}/{args.finalstate}_mdst.root",
        # additionalBranches=additional_br,
    )

    # Save all dataobjects
    # main.add_module("RootOutput", outputFileName=f"{args.outputdir}/{args.finalstate}_rec.root")

    # Print modules in path
    # basf2.print_path(main)

    # Run event loop
    basf2.process(main)
    # print(basf2.statistics)


if __name__ == "__main__":
    main()
