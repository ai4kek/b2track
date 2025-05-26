#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Descriptor: MC16rd_prompt (GitLab: Issue-96) - Phase: eph3 mixed (Run Dependent BG)

#############################################################
# Steering file for official MC production of signal samples
#
# April 2021 - Belle II Collaboration
# ############################################################

import glob as glob

import basf2 as b2
import generators as ge
import L1trigger as l1
import mdst as mdst
import reconstruction as re
import simulation as si


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run-dependent MC (similar as MC16rd-prompt)."
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

    # set database conditions (in addition to default)
    b2.conditions.override_globaltags()
    b2.conditions.append_globaltag("mcrd_prompt_rel08")
    b2.conditions.append_globaltag("data_prompt_rel08")
    b2.conditions.append_globaltag("online")

    # background (collision) files
    bg = glob.glob("./*.root")

    # if running locally e.g. on KEKCC/NAF clusters
    bg_local = glob.glob(
        "/group/belle2/dataprod/BGOverlay/BGOrd/rel8/BGOExp35rel8/release-08-02-05/e0035/4S/r*/beambg/sub*/*"
    )

    # create path
    main = b2.create_path()

    # specify number of events to be generated
    main.add_module("EventInfoSetter", expList=35, runList=1749, evtNumList=131385)

    # events generator
    ge.add_evtgen_generator(path=main, finalstate="mixed", eventType="mixed")

    # detector simulation
    si.add_simulation(main, bkgfiles=bg)

    # reconstruction
    # re.add_reconstruction(main)

    # Finally add mdst output
    # mdst.add_mdst_output(main, additionalBranches=['EventExtraInfo'], filename="mdst.root")

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
