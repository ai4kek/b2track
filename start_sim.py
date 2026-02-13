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
import background
import glob as glob
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
    b2.set_random_seed(12345)

    # Set database conditions (in addition to default) for MCrd
    b2.conditions.override_globaltags()
    b2.conditions.append_globaltag("mcrd_prompt_rel08")
    b2.conditions.append_globaltag("data_prompt_rel08")
    b2.conditions.append_globaltag("online")

    # FIXME (1): Custom CDC geometry through a payload (c.f. cdc-utilities)
    # Payload is created using: exp=35, run=1853, global_tag='online'
    # b2.conditions.prepend_testing_payloads("./localdb/database.txt")

    # Steering Path
    main = b2.Path()

    # For MCrd, use exp # 35 and run # 1853, special payload needed.
    main.add_module("EventInfoSetter", evtNumList=[1000], expList=[35], runList=[1853])

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
    # bg_files = background.get_background_files(
    #    folder=None,  # None >> BELLE2_BACKGROUND_DIR, or set otherwise
    #    output_file_info=True,
    # )

    # Or, add run-dependent backgroud
    bg_local = glob.glob(
        "/group/belle2/dataprod/BGOverlay/BGOrd/rel8/BGOExp35rel8/release-08-02-05/e0035/4S/r01853/beambg/sub*/*"
    )

    # Add simulation
    si.add_simulation(
        path=main,
        components=None,
        bkgfiles=None,  # to add background set bkgfiles=bg_files
        bkgOverlay=True,
    )

    # FIXME (2): Custom CDC geometry through TFCDC_WireHitPreparer
    # sl_to_use = [0, 1, 2, 5, 6, 7, 8, 9]
    # basf2.set_module_parameters(
    #    main, name="TFCDC_WireHitPreparer", useSuperLayers=sl_to_use)

    # Save all dataobjects
    main.add_module("RootOutput", outputFileName=args.output)

    # Print modules in path
    # b2.print_path(main)

    # Run event loop
    b2.process(main)
    # print(b2.statistics)


if __name__ == "__main__":
    main()
