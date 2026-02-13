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
import basf2 as b2
import generators as ge


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run-independent MC (similar to MC16ri samples)."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dataset/mixed_gen.root",
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

    # Save all dataobjects
    main.add_module("RootOutput", outputFileName=args.output)

    # Print modules in path
    b2.print_path(main)

    # Run event loop
    b2.process(main)
    # print(b2.statistics)


if __name__ == "__main__":
    main()
