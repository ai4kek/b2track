#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
import background as bkg
import basf2 as b2
import generators as ge
import simulation as si


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run-independent MC (similar to MC16ri samples)."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dataset/mixed_mcri.root",
        help="Output ROOT file path (default: %(default)s)",
    )
    parser.add_argument(
        "--finalstate",
        type=str,
        default="mixed",
        help="Final state type (default: %(default)s)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Reproducibility
    b2.set_random_seed(12345)

    # Steering Path
    main = b2.Path()

    # MCri settings, choose exp number 0/1003/1004 and run number 0
    main.add_module("EventInfoSetter", evtNumList=[1000], expList=[0], runList=[0])

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
    bkg_files = bkg.get_background_files(
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
    main.add_module("RootOutput", outputFileName=args.output)

    # Print modules in path
    # b2.print_path(main)

    # Run event loop
    b2.process(main)
    # print(b2.statistics)


if __name__ == "__main__":
    main()
