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

# TODO: How to visualize wire efficiency map of CDC for an experiment?
# See "cdc-utilities" repository from Giaccomo from KIT to visualize CDC.
# TODO: How to switch on-off some parts of the CDC?
# See "cdc-utilities" repository from Giaccomo from KIT to visualize CDC.
# TODO: How to prepend a globaltag? (see Section 5.4 of basf2 docs)

import argparse
import background
import basf2
import generators as ge
import simulation as si


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run-independent MC (similar to MC16ri samples)."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dataset/mixed_sim.root",
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
    basf2.set_random_seed(12345)

    # Add custom CDC geometry through a payload (from cdc-utilities
    # repository). Prepend a local payload for custom CDC geometry
    basf2.conditions.prepend_testing_payloads("./localdb/database.txt")

    # Steering Path
    main = basf2.Path()

    # For MCrd, use exp # 35 and any run no. > 1500, special payload needed.
    main.add_module("EventInfoSetter", evtNumList=[
                    1000]) # , expList=[35], runList=[1853])

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
    # bkg_files = background.get_background_files(
    #    folder=None,  # None >> BELLE2_BACKGROUND_DIR, or set otherwise
    #    output_file_info=True,
    # )

    # Or, add run-dependent backgroud, on KEKCC
    # bkg_files = glob.glob(
    #    "/group/belle2/dataprod/BGOverlay/BGOrd/rel8/BGOExp35rel8/release-08-02-05/e0035/4S/r01853/beambg/sub*/*"
    # )

    # Add simulation
    si.add_simulation(
        path=main,
        components=None,
        bkgfiles=None,  # to add background set bkgfiles=bkg_files
        bkgOverlay=True,
    )

    # Save all dataobjects
    main.add_module("RootOutput", outputFileName=args.output)

    # Print modules in path
    # basf2.print_path(main)

    # Run event loop
    basf2.process(main)
    # print(basf2.statistics)


if __name__ == "__main__":
    main()
