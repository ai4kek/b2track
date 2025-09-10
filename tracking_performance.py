#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

"""
To run this script:
basf2 tracking_performance.py -- -p mixed -i dataset/mixed_mdst.root
"""

import os
from argparse import ArgumentParser

import basf2 as b2
import modularAnalysis as ma
from variables import variables as vm


def setup_aliases():
    """Setup variable aliases for tracking metrics"""
    vm.addAlias("pRes", "formula(mcP-p)")
    vm.addAlias("ptRes", "formula(mcPT-pt)")
    vm.addAlias("pPull", "formula((mcP-p)/pErr)")
    vm.addAlias("ptPull", "formula((mcPT-pt)/ptErr)")
    vm.addAlias("d0Res", "formula(d0Pull*d0Err)")
    vm.addAlias("z0Res", "formula(z0Pull*z0Err)")
    vm.addAlias("phi0Res", "formula(phi0Pull*phi0Err)")
    vm.addAlias("tanLambdaRes", "formula(tanLambdaPull*tanLambdaErr)")
    vm.addAlias("omegaRes", "formula(omegaPull*omegaErr)")

    vm.addAlias("mcX", "mcProductionVertexX")
    vm.addAlias("mcY", "mcProductionVertexY")
    vm.addAlias("mcZ", "mcProductionVertexZ")


def create_ntuples(path, output_file):
    """Create ntuples for MC and reconstructed tracks"""
    # Setup variables for ntuples
    # MC variables
    v_kin_MC = ["mcPX", "mcPY", "mcPZ"]
    v_kin_MC += ["mcX", "mcY", "mcZ", "mcPDG"]
    v_FOMs_MC = ["isPrimarySignal", "seenInCDC", "seenInSVD", "mcPDG"]

    # RECO variables (some MC info)
    v_kin = v_kin_MC + ["px", "py", "pz"]
    v_kin += ["x", "y", "z"]
    v_FOMs = v_FOMs_MC + [
        "isSignal",
        "mcSecPhysProc",
        "isCloneTrack",
        "isTrackFlippedAndRefitted",
        "charge",
    ]

    # MC Ntuples
    ma.variablesToNtuple(
        decayString="pi+:gen",
        variables=v_kin_MC + v_FOMs_MC,
        treename="MCpions",
        filename=output_file,
        path=path,
    )

    # Reco Ntuples (also contain some MC info)
    ma.variablesToNtuple(
        decayString="pi+:all",
        variables=v_kin + v_FOMs,
        treename="pions",
        filename=output_file,
        path=path,
    )


def create_histograms(path, output_file):
    """Create histograms for tracking performance"""
    # Resolution
    particle_based_h1D = [
        ("pPull", 200, -6.0, 6.0),
        ("ptPull", 200, -6.0, 6.0),
        ("pRes", 200, -0.5, 0.5),
        ("ptRes", 200, -0.5, 0.5),
    ]

    checks_h1D = [
        ("nPXDHits", 5, 0, 5),
        ("nSVDHits", 16, 0, 16),
        ("nCDCHits", 200, 0, 200),
    ]

    # For pions we save additional 1D variables: pulls (5 helix parameters, p, and pt)
    pions_h1D = (
        particle_based_h1D
        + checks_h1D
        + [
            ("d0Pull", 200, -6.0, 6.0),
            ("z0Pull", 200, -6.0, 6.0),
            ("omegaPull", 200, -6.0, 6.0),
            ("phi0Pull", 200, -6.0, 6.0),
            ("tanLambdaPull", 200, -6.0, 6.0),
            ("d0Res", 200, -0.05, 0.05),
            ("z0Res", 200, -0.05, 0.05),
            ("omegaRes", 200, -0.05, 0.05),
            ("phi0Res", 200, -0.05, 0.05),
            ("tanLambdaRes", 200, -0.05, 0.05),
        ]
    )

    particle_based_h2D = [
        ("pRes", 100, -0.5, 0.5, "charge", 3, -1.5, 1.5),
        ("pPull", 100, -1.5, 1.5, "charge", 3, -1.5, 1.5),
        ("p", 100, 0.0, 4.0, "pRes", 100, -0.5, 0.5),
        ("p", 100, 0.0, 4.0, "pPull", 100, -1.5, 1.5),
        ("ptRes", 100, -0.5, 0.5, "charge", 3, -1.5, 1.5),
        ("ptPull", 100, -1.5, 1.5, "charge", 3, -1.5, 1.5),
        ("pt", 100, 0.0, 4.0, "ptRes", 100, -0.5, 0.5),
        ("pt", 100, 0.0, 4.0, "ptPull", 100, -1.5, 1.5),
    ]

    pions_h2D = particle_based_h2D + [
        ("d0Pull", 200, -6.0, 6.0, "nPXDHits", 5, 0, 5.0),
        ("z0Pull", 200, -6.0, 6.0, "nPXDHits", 5, 0, 5.0),
        ("d0Res", 200, -0.05, 0.05, "nPXDHits", 5, 0, 5.0),
        ("z0Res", 200, -0.05, 0.05, "nPXDHits", 5, 0, 5.0),
        ("p", 100, 0.0, 4.0, "d0Res", 200, -0.05, 0.05),
        ("p", 100, 0.0, 4.0, "z0Res", 200, -0.05, 0.05),
    ]

    ma.variablesToHistogram(
        decayString="pi+:matched",
        variables=pions_h1D,
        variables_2d=pions_h2D,
        filename=output_file,
        path=path,
        directory="pions",
    )

    ma.variablesToHistogram(
        decayString="K+:matched",
        variables=particle_based_h1D,
        variables_2d=particle_based_h2D,
        filename=output_file,
        path=path,
        directory="kaons",
    )

    ma.variablesToHistogram(
        decayString="p+:matched",
        variables=particle_based_h1D,
        variables_2d=particle_based_h2D,
        filename=output_file,
        path=path,
        directory="protons",
    )


def parse_args():
    """Parse command line arguments."""
    parser = ArgumentParser(description=__doc__)

    parser.add_argument(
        "-p",
        "--prefix",
        type=str,
        default="mixed",
        help="Prefix for output files. Default: %(default)s",
    )
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        default="mixed_reco.root",
        help="Input ROOT file from reconstruction. Default: %(default)s",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="validation",
        help="Output directory (Default: %(default)s)",
    )
    return parser.parse_args()


def main(args):

    # Setup variable aliases
    setup_aliases()

    # Create the steering path
    main = b2.Path()

    # Add progress reporting
    main.add_module("Progress")

    # Handle input file
    input_file = args.input
    if os.path.exists(input_file):
        filelist = [input_file]
    else:
        filelist = [b2.find_file(input_file, "examples", False)]

    # Handle output
    os.makedirs(args.output, exist_ok=True)

    # Input the mDST
    ma.inputMdstList(filelist=filelist, environmentType="default", path=main)

    # Create particle lists
    pionsMC = ("pi+:gen", "")
    ma.fillParticleListsFromMC([pionsMC], path=main)

    pions = ("pi+:all", "")
    kaons = ("K+:matched", "isPrimarySignal == 1")
    protons = ("p+:matched", "isPrimarySignal == 1")

    ma.fillParticleLists([pions, kaons, protons], path=main)
    ma.cutAndCopyList("pi+:matched", "pi+:all", cut="isPrimarySignal==1", path=main)

    # Setup output file names
    ntuple_file = f"{args.output}/{args.prefix}_ntuple.root"
    histogram_file = f"{args.output}/{args.prefix}_hist.root"

    # Create ntuples
    create_ntuples(main, output_file=ntuple_file)

    # Create histograms
    create_histograms(main, output_file=histogram_file)

    # Process the path
    b2.process(main)
    print(b2.statistics)


if __name__ == "__main__":
    args = parse_args()
    print(f"Running with arguments:{args}")
    main(args)
