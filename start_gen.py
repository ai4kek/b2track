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
import generators as ge


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run SVD tracking with specified parameters"
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

    # Set expList=[0] or [12] or custom, need a specific globaltag/payload.
    # For run-independent Monte Carlo simulation set runList=[0] below.
    main.add_module("EventInfoSetter", evtNumList=[
                    1000], expList=[0], runList=[0])

    # MC sample: 'mixed' (BBbar), 'charged' (B+B-), 'mu+mu-' (dimuon), 'tau+tau-'

    # Add EvtGen generator
    if args.finalstate in ["mixed", "charged"]:
        ge.add_evtgen_generator(
            path=main,
            finalstate=args.finalstate,
            signaldecfile=None,
        )
    # Add KKMC generator
    elif args.finalstate in ["mu+mu-", "tau+tau-"]:
        ge.add_kkmc_generator(
            path=main,
            finalstate=args.finalstate,
            signalconfigfile="",
        )
    else:
        raise ValueError(f"Unknown finalstate: {args.finalstate}.")

    # Save all dataobjects
    main.add_module(
        "RootOutput", outputFileName=f"{args.outputdir}/{args.finalstate}_gen.root"
    )

    # Print modules in path
    # basf2.print_path(main)

    # Run event loop
    basf2.process(main)
    # print(basf2.statistics)


if __name__ == "__main__":
    main()
