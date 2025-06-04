#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

"""
Run-independent (MC16ri) | Run-dependent (MC16rd)
- simulated background   | - background overlay from data
- exp 0 = nominal lumi   | - realistic detector conditions
- exp 1003 = pre-LS1     | - produced with release-08-02 (Run 1)
- exp 1004 = pre-LS2     | - produced with release-08-03 (Run 2)
"""

# TODO: How to prepend a globaltag? (see Section 5.4 of basf2 docs)
# TODO: How to add background to simulation? (see Section 9. of basf2 docs)
# TODO: How to visualize wire efficiency map of CDC for an experiment?
# TODO: How to switch on-off some parts of the CDC?


import argparse

import background
import basf2
import generators as ge
import simulation as si


def parse_args():
    parser = argparse.ArgumentParser(description="Run-independent MC (MC16ri-like).")
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

    # MCri settings, chose exp number 0/1003/1004 and run number 0. For MCrd, use
    # exp number 35 and any run number after 1500, it requires a special payload.
    main.add_module("EventInfoSetter", evtNumList=[1000], expList=[0], runList=[0])

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

    # Add simulated beam background
    bkg_files = background.get_background_files(
        folder=None,  # None >> BELLE2_BACKGROUND_DIR, or set otherwise
        output_file_info=True,
    )

    # Add simulation
    si.add_simulation(
        path=main,
        components=None,
        bkgfiles=bkg_files,  # to add background set bkgfiles=bkg_files
        bkgOverlay=True,
    )

    # Save all dataobjects
    main.add_module(
        "RootOutput", outputFileName=f"{args.outputdir}/{args.finalstate}_sim.root"
    )

    # Print modules in path
    # basf2.print_path(main)

    # Run event loop
    basf2.process(main)
    # print(basf2.statistics)


if __name__ == "__main__":
    main()
