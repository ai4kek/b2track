#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

# Intended to run with a dispatcher script as a subprocess for different
# trails with specific params. For simple tracking, run the start_rec.py.

import argparse
import json

import basf2
import svd
from tracking.path_utils import add_mc_matcher, add_vxd_track_finding_vxdtf2

from src.tracking_evalution import TrackEvaluation
from src.tracking_metrics import TrackMetrics
from src.utils import print_module_params


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
        "--params",
        type=str,
        default="params.json",
        help="Input parameters JSON file (default: params.json)",
    )
    parser.add_argument(
        "--metrics",
        type=str,
        default="metrics.csv",
        help="Output metrics CSV file (default: metrics.csv)",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # Reproducibility
    basf2.set_random_seed(12345)

    # Steering Path
    main = basf2.Path()

    # Add RootInput to load simulated data
    main.add_module("RootInput", inputFileName=args.input)

    # SVD-only Tracking (see run_tracking.py for full tracking)
    main.add_module("Gearbox")
    main.add_module("Geometry")

    main.add_module("SetupGenfitExtrapolation",
                    energyLossBrems=False, noiseBrems=False)

    svd.add_svd_reconstruction(main)
    add_vxd_track_finding_vxdtf2(
        main, reco_tracks="RecoTracksSVD", components=["SVD"])
    main.add_module("DAFRecoFitter", recoTracksStoreArrayName="RecoTracksSVD")

    main.add_module(
        "TFCDC_WireHitPreparer",
        wirePosition="aligned",
        useSecondHits=False,
        flightTimeEstimation="outwards",
    )

    # ToCDCCKF module
    main.add_module(
        "ToCDCCKF",
        inputWireHits="CDCWireHitVector",
        inputRecoTrackStoreArrayName="RecoTracksSVD",
        relatedRecoTrackStoreArrayName="CKFCDCRecoTracks",
        relationCheckForDirection="backward",
        outputRecoTrackStoreArrayName="CKFCDCRecoTracks",
        outputRelationRecoTrackStoreArrayName="RecoTracksSVD",
        writeOutDirection="backward",
        stateBasicFilterParameters={"maximalHitDistance": 0.75},
        stateExtrapolationFilterParameters={"direction": "forward"},
        pathFilter="arc_length",
    )

    main.add_module(
        "RelatedTracksCombiner",
        CDCRecoTracksStoreArrayName="CKFCDCRecoTracks",
        VXDRecoTracksStoreArrayName="RecoTracksSVD",
        recoTracksStoreArrayName="RecoTracks",
    )

    main.add_module("DAFRecoFitter", recoTracksStoreArrayName="RecoTracks")
    main.add_module("TrackCreator", recoTrackColName="RecoTracks")

    # Adding MCMatcher after TrackCreator
    add_mc_matcher(main)

    # Load ToCDCCKF parameter set
    with open(args.params, "r") as f:
        params = json.load(f)

    # Inject parameters into ToCDCCKF
    basf2.set_module_parameters(
        main, name="ToCDCCKF", recursive=True, **params)

    # Print new prameters, don't use basf2.print_params() rather use this wrapper
    # print_module_params(main, "ToCDCCKF")

    # Calculate tracking metrics
    # metrics = TrackMetrics(params, args.finalstate, filename=args.metrics)
    metrics = TrackEvaluation(params, args.finalstate, filename=args.metrics)
    main.add_module(metrics)

    # Save mDST dataobjects (not required for search)
    # mdst.add_mdst_output(main, mc=True, filename=f"dataset/{finalstate}_mdst_svd.root")

    # Save all dataobjects (not required for search)
    # main.add_module("RootOutput", outputFileName=f"dataset/{finalstate}_reco_svd.root")

    basf2.process(main)
    # print(basf2.statistics)


if __name__ == "__main__":
    main()
