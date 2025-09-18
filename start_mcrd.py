#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Descriptor: MC16rd_prompt (GitLab: Issue-96) - Phase: eph3 mixed (Run Dependent BG)

#############################################################
# Steering file for official MC production of signal samples
#
# April 2021 - Belle II Collaboration
# ############################################################

import argparse
import glob as glob

import basf2 as b2
import generators as ge
import L1trigger as l1
import mdst as mdst
import reconstruction as re
import simulation as si


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run-dependent MC (similar to MC16rd-prompt samples)."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dataset/mixed_mcrd.root",
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

    # Set seed for reproducibility
    b2.set_random_seed(12345)

    # Set database conditions (in addition to default)
    b2.conditions.override_globaltags()
    b2.conditions.append_globaltag("mcrd_prompt_rel08")
    b2.conditions.append_globaltag("data_prompt_rel08")
    b2.conditions.append_globaltag("online")

    # Steering Path
    main = b2.create_path()

    # For MCrd, use exp # 35 and any run number > 1500, special payload needed.
    main.add_module("EventInfoSetter", evtNumList=[
                    9528], expList=[35], runList=[1853])

    # Events generator
    if args.finalstate in ["mixed", "charged"]:
        ge.add_evtgen_generator(  # Add EvtGen generator
            path=main,
            finalstate=args.finalstate,
            signaldecfile=None,
        )
    elif args.finalstate in ["mu+mu-", "tau+tau-"]:
        ge.add_kkmc_generator(  # Add KKMC generator
            path=main,
            finalstate=args.finalstate,
            signalconfigfile="",
        )
    else:
        raise ValueError(f"Unknown finalstate: {args.finalstate}.")

    # Add Background
    # background (collision) files
    bg = glob.glob("./*.root")

    # if running locally e.g. on KEKCC/NAF clusters
    bg_local = glob.glob(
        "/group/belle2/dataprod/BGOverlay/BGOrd/rel8/BGOExp35rel8/release-08-02-05/e0035/4S/r01853/beambg/sub*/*"
    )

    # Add simulation
    si.add_simulation(
        path=main,
        components=None,
        bkgfiles=bg_local,
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
