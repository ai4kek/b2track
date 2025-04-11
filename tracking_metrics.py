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
basf2 tracking_metrics.py -- -f1 mixed/mixed_ntuple.root -p1 mixed
"""

import argparse
import math
import os
import pickle
import sys

import matplotlib.pyplot as plt
import numpy as np
import uproot
from matplotlib.backends.backend_pdf import PdfPages

# ===============================================

# sys.path.append('/home/belle2/scavino/th_Performance/tracking_validation/')
sys.path.append("../")
import src.custom_functions as cf

# ===============================================


def get_dataframes(
    rootfile,
    mc_tree="MCpions;1",
    reco_tree="pions;1",
):

    uproot_file = uproot.open(rootfile)

    t_MCpions = uproot_file[mc_tree]
    t_pions = uproot_file[reco_tree]

    MCarr_list, arr_list = [], []
    for k in t_MCpions.keys():
        if "__" not in k:
            MCarr_list.append(k)
    for k in t_pions.keys():
        if "__" not in k:
            arr_list.append(k)

    mc_df = t_MCpions.arrays(MCarr_list, library="pd")
    reco_df = t_pions.arrays(arr_list, library="pd")

    return mc_df, reco_df


def add_variables_to_mcdf(mc_df):
    mc_df["mcP"] = cf.p(mc_df["mcPX"], mc_df["mcPY"], mc_df["mcPZ"])
    mc_df["mcPT"] = cf.pt(mc_df["mcPX"], mc_df["mcPY"])
    mc_df["mcCosTheta"] = cf.costheta(mc_df["mcPX"], mc_df["mcPY"], mc_df["mcPZ"])
    mc_df["mcPhi"] = cf.phi(mc_df["mcPX"], mc_df["mcPY"])


def add_variables_to_recodf(reco_df):
    reco_df["p"] = cf.p(reco_df["px"], reco_df["py"], reco_df["pz"])
    reco_df["pt"] = cf.pt(reco_df["px"], reco_df["py"])
    reco_df["cosTheta"] = cf.costheta(reco_df["px"], reco_df["py"], reco_df["pz"])
    reco_df["phi"] = cf.phi(reco_df["px"], reco_df["py"])

    reco_df["mcP"] = cf.p(reco_df["mcPX"], reco_df["mcPY"], reco_df["mcPZ"])
    reco_df["mcPT"] = cf.pt(reco_df["mcPX"], reco_df["mcPY"])
    reco_df["mcCosTheta"] = cf.costheta(
        reco_df["mcPX"], reco_df["mcPY"], reco_df["mcPZ"]
    )
    reco_df["mcPhi"] = cf.phi(reco_df["mcPX"], reco_df["mcPY"])


def mcdf_for_foms(mc_df):
    MCpions_tightMatch = mc_df.query("isPrimarySignal==1")
    MCpions_tightMatch_plus = mc_df.query("isPrimarySignal==1 and mcPDG == 211")
    MCpions_tightMatch_minus = mc_df.query("isPrimarySignal==1 and mcPDG == -211")
    return MCpions_tightMatch, MCpions_tightMatch_plus, MCpions_tightMatch_minus


def recodf_for_foms(reco_df):
    pions_tightMatch = reco_df.query("isPrimarySignal==1 and isCloneTrack==0")
    pions_tightMatch_plus = pions_tightMatch.query("charge>0.")
    pions_tightMatch_minus = pions_tightMatch.query("charge<0.")
    pions_looseMatch = reco_df.query(
        "abs(mcPDG)==211 and mcSecPhysProc==0 and (isSignal==0 or isSignal ==1) and isCloneTrack==0"
    )
    pions_wrongMatch = pions_looseMatch.query("isSignal == 0")
    pions_fake = reco_df.query("isSignal!=0 and isSignal!=1")
    pions_clone = reco_df.query("isCloneTrack==1")
    pions_wRelationToMC = reco_df.query("isSignal==0 or isSignal==1")
    pions_flipRefit = reco_df.query("isTrackFlippedAndRefitted==1")
    pions_tigthMatch_flipRefit = pions_tightMatch.query("isTrackFlippedAndRefitted==1")
    pions_tigthMatch_flipRefit_plus = pions_tightMatch_plus.query(
        "isTrackFlippedAndRefitted==1"
    )
    pions_tigthMatch_flipRefit_minus = pions_tightMatch_minus.query(
        "isTrackFlippedAndRefitted==1"
    )
    pions_looseMatch_flipRefit = pions_looseMatch.query("isTrackFlippedAndRefitted==1")
    pions_wrongMatch_flipRefit = pions_wrongMatch.query("isTrackFlippedAndRefitted==1")
    pions_toBeFlipped = pions_looseMatch.query(
        "isTrackFlippedAndRefitted==1 or isSignal == 0"
    )  # (pions_looseMatch_flipRefit or pions_wrongMatch)

    pions_list = [
        pions_tightMatch,
        pions_tightMatch_plus,
        pions_tightMatch_minus,
        pions_looseMatch,
        pions_wrongMatch,
    ]
    pions_list += [pions_fake, pions_clone, pions_wRelationToMC]
    pions_list += [
        pions_flipRefit,
        pions_tigthMatch_flipRefit,
        pions_tigthMatch_flipRefit_plus,
        pions_tigthMatch_flipRefit_minus,
        pions_looseMatch_flipRefit,
        pions_wrongMatch_flipRefit,
        pions_toBeFlipped,
    ]
    return pions_list


def mcdf_for_foms_seen(mc_df):
    seen = "(seenInSVD==1 or seenInCDC==1)"
    MCpions_tightMatch = mc_df.query(f"isPrimarySignal==1 and {seen}")
    MCpions_tightMatch_plus = mc_df.query(
        f"isPrimarySignal==1 and mcPDG == 211 and {seen}"
    )
    MCpions_tightMatch_minus = mc_df.query(
        f"isPrimarySignal==1 and mcPDG == -211 and {seen}"
    )
    return MCpions_tightMatch, MCpions_tightMatch_plus, MCpions_tightMatch_minus


def recodf_for_foms_seen(reco_df):
    seen = "(seenInSVD==1 or seenInCDC==1)"
    pions_tightMatch = reco_df.query(
        f"isPrimarySignal==1 and isCloneTrack==0 and {seen}"
    )
    pions_tightMatch_plus = pions_tightMatch.query("charge>0.")
    pions_tightMatch_minus = pions_tightMatch.query("charge<0.")
    pions_looseMatch = reco_df.query(
        f"abs(mcPDG)==211 and mcSecPhysProc==0 and (isSignal==0 or isSignal ==1) and isCloneTrack==0 and {seen}"
    )
    pions_wrongMatch = pions_looseMatch.query("isSignal == 0")
    pions_fake = reco_df.query(
        "isSignal!=0 and isSignal!=1"
    )  # seen for fakes make no sense
    pions_clone = reco_df.query(f"isCloneTrack==1 and {seen}")
    pions_wRelationToMC = reco_df.query(f"(isSignal==0 or isSignal==1) and {seen}")
    pions_flipRefit = reco_df.query(f"isTrackFlippedAndRefitted==1 and {seen}")
    pions_tigthMatch_flipRefit = pions_tightMatch.query("isTrackFlippedAndRefitted==1")
    pions_tigthMatch_flipRefit_plus = pions_tightMatch_plus.query(
        "isTrackFlippedAndRefitted==1"
    )
    pions_tigthMatch_flipRefit_minus = pions_tightMatch_minus.query(
        "isTrackFlippedAndRefitted==1"
    )
    pions_looseMatch_flipRefit = pions_looseMatch.query("isTrackFlippedAndRefitted==1")
    pions_wrongMatch_flipRefit = pions_wrongMatch.query("isTrackFlippedAndRefitted==1")
    pions_toBeFlipped = pions_looseMatch.query(
        "isTrackFlippedAndRefitted==1 or isSignal == 0"
    )  # (pions_looseMatch_flipRefit or pions_wrongMatch)

    pions_list = [
        pions_tightMatch,
        pions_tightMatch_plus,
        pions_tightMatch_minus,
        pions_looseMatch,
        pions_wrongMatch,
    ]
    pions_list += [pions_fake, pions_clone, pions_wRelationToMC]
    pions_list += [
        pions_flipRefit,
        pions_tigthMatch_flipRefit,
        pions_tigthMatch_flipRefit_plus,
        pions_tigthMatch_flipRefit_minus,
        pions_looseMatch_flipRefit,
        pions_wrongMatch_flipRefit,
        pions_toBeFlipped,
    ]
    return pions_list


def plots(rootfile, sample="test", seen=True, savefig=True, figsize=(14, 10)):

    mc_df, reco_df = get_dataframes(rootfile)

    add_variables_to_mcdf(mc_df)
    add_variables_to_recodf(reco_df)

    if seen:
        MCpions_tightMatch, MCpions_tightMatch_plus, MCpions_tightMatch_minus = (
            mcdf_for_foms_seen(mc_df)
        )
        pions_list = recodf_for_foms_seen(reco_df)

    else:
        MCpions_tightMatch, MCpions_tightMatch_plus, MCpions_tightMatch_minus = (
            mcdf_for_foms(mc_df)
        )
        pions_list = recodf_for_foms(reco_df)

    (
        pions_tightMatch,
        pions_tightMatch_plus,
        pions_tightMatch_minus,
        pions_looseMatch,
        pions_wrongMatch,
    ) = pions_list[0:5]
    pions_fake, pions_clone, pions_wRelationToMC = pions_list[5:8]
    (
        pions_flipRefit,
        pions_tigthMatch_flipRefit,
        pions_tigthMatch_flipRefit_plus,
        pions_tigthMatch_flipRefit_minus,
        pions_looseMatch_flipRefit,
        pions_wrongMatch_flipRefit,
        pions_toBeFlipped,
    ) = pions_list[8:]

    if savefig:
        if not os.path.exists(sample):
            os.makedirs(sample)

    dictionary = {}
    dictionary["sample"] = sample
    dictionary["xvariable"] = "costheta"
    dictionary["yvariable"] = "pt"

    figs = []
    # For table
    data, rows = [], []
    # columns = ('central value', r'$\sigma$')

    x_v, y_v = "mcCosTheta", "mcPT"
    x_l, y_l = r"cos$\theta_{MC}$", "p$_{t,MC}$ [GeV/c]"
    x_b = 6
    y_b = [
        0.0,
        0.05,
        0.1,
        0.15,
        0.2,
        0.25,
        0.3,
        0.4,
        0.5,
        0.6,
        0.7,
        0.8,
        0.9,
        1.0,
        1.5,
        2.0,
    ]
    x_r, y_r = (-1, 1), (0.0, 2.0)  # (0,1)

    x, y, h1, h2, nEntries, fig, fig1 = cf.normalized_2D(
        MCpions_tightMatch,
        x_var=x_v,
        y_var=y_v,
        x_label=x_l,
        y_label=y_l,
        cbar_label="Fraction of MCParticles",
        bins_x=x_b,
        bins_y=y_b,
        range_x=x_r,
        range_y=y_r,
        cmap="plasma",
        vmin=0,
        vmax=0.05,
        color_text="white",
        size_text=14,
        figsize=figsize,
        savefig=savefig,
        percent=True,
        figname=f"{sample}/MCPions",
        fignamefrac=f"{sample}/MCPionsFraction",
        closefig=False,
    )
    figs.append(fig)
    figs.append(fig1)

    # finding charge efficiency
    print("finding charge efficiency")
    x, y, r, err_r, h_n1, h_n2, roverall, err_roverall, fig, pc = cf.ratio_2D(
        pions_tightMatch,
        MCpions_tightMatch,
        x_var=x_v,
        y_var=y_v,
        x_label=x_l,
        y_label=y_l,
        cbar_label="Finding charge efficiency",
        bins_x=x_b,
        bins_y=y_b,
        range_x=x_r,
        range_y=y_r,
        cmap="YlGn",
        vmin=0,
        vmax=1,
        color_text="white",
        color_text2="black",
        threshold=0.5,
        size_text=14,
        figsize=figsize,
        savefig=savefig,
        figname=f"{sample}/FCE",
        savefigerr=savefig,
        errfigname=f"{sample}/err_FCE",
        offsetx=0.2,
        offsety=0.2,
        percent=True,
        closefig=False,
    )
    dictionary["xedges"], dictionary["yedges"] = h_n1, h_n2
    (
        dictionary["FCE_overall"],
        dictionary["err_FCE_overall"],
        dictionary["FCE"],
        dictionary["err_FCE"],
    ) = (roverall, err_roverall, r, err_r)
    figs.append(fig)
    data.append([roverall, err_roverall])
    # rows.append('FCE')
    rows.append("   Finding Charge Efficiency   ")

    # finding efficiency
    print("finding efficiency")
    x, y, r, err_r, h_n1, h_n2, roverall, err_roverall, fig, pc = cf.ratio_2D(
        pions_looseMatch,
        MCpions_tightMatch,
        x_var=x_v,
        y_var=y_v,
        x_label=x_l,
        y_label=y_l,
        cbar_label="Finding efficiency",
        bins_x=x_b,
        bins_y=y_b,
        range_x=x_r,
        range_y=y_r,
        cmap="YlGn",
        vmin=0,
        vmax=1,
        color_text="white",
        color_text2="black",
        threshold=0.5,
        size_text=14,
        figsize=figsize,
        savefig=savefig,
        figname=f"{sample}/FE",
        savefigerr=savefig,
        errfigname=f"{sample}/err_FE",
        offsetx=0.2,
        offsety=0.2,
        percent=True,
        closefig=False,
    )

    print("ratio (overall):", f"{roverall:.6f} +- {err_roverall:.6f}")

    (
        dictionary["FE_overall"],
        dictionary["err_FE_overall"],
        dictionary["FE"],
        dictionary["err_FE"],
    ) = (roverall, err_roverall, r, err_r)
    figs.append(fig)
    data.append([roverall, err_roverall])
    # rows.append('FE')
    rows.append("Finding Efficiency (Overall)")

    # charge efficiency
    print("charge efficiency")
    x, y, r, err_r, h_n1, h_n2, roverall, err_roverall, fig, pc = cf.ratio_2D(
        pions_tightMatch,
        pions_looseMatch,
        x_var=x_v,
        y_var=y_v,
        x_label=x_l,
        y_label=y_l,
        cbar_label="Charge efficiency",
        bins_x=x_b,
        bins_y=y_b,
        range_x=x_r,
        range_y=y_r,
        cmap="YlGn",
        vmin=0,
        vmax=1,
        color_text="white",
        color_text2="black",
        threshold=0.5,
        size_text=14,
        figsize=figsize,
        savefig=savefig,
        figname=f"{sample}/CE",
        savefigerr=savefig,
        errfigname=f"{sample}/err_CE",
        offsetx=0.2,
        offsety=0.2,
        percent=True,
        closefig=False,
    )
    (
        dictionary["CE_overall"],
        dictionary["err_CE_overall"],
        dictionary["CE"],
        dictionary["err_CE"],
    ) = (roverall, err_roverall, r, err_r)
    figs.append(fig)
    data.append([roverall, err_roverall])
    # rows.append('CE')
    rows.append("Charge Efficiency")

    # From now on we need reconstructed values (instead of MC)
    x_v, y_v = "cosTheta", "pt"
    x_l, y_l = r"cos$\theta_{reco}$", "p$_{t,reco}$ [GeV/c]"

    # charge asymetry
    x, y, r, err_r, h_n1, h_n2, roverall, err_roverall, fig, pc = cf.chargeasym_2D(
        pions_tightMatch_plus,
        pions_tightMatch_minus,
        x_var=x_v,
        y_var=y_v,
        x_label=x_l,
        y_label=y_l,
        bins_x=x_b,
        bins_y=y_b,
        range_x=x_r,
        range_y=y_r,
        color_text="black",
        color_text2="black",
        threshold=-0.5,
        size_text=14,
        figsize=figsize,
        savefig=savefig,
        figname=f"{sample}/CA",
        savefigerr=savefig,
        errfigname=f"{sample}/err_CA",
        offsetx=0.2,
        offsety=0.2,
        percent=True,
        closefig=False,
    )
    (
        dictionary["CA_overall"],
        dictionary["err_CA_overall"],
        dictionary["CA"],
        dictionary["err_CA"],
    ) = (roverall, err_roverall, r, err_r)
    figs.append(fig)
    data.append([roverall, err_roverall])
    # rows.append('CA')
    rows.append("Charge Asymmetry")

    # fake rate
    print("fake rate")
    x, y, r, err_r, h_n1, h_n2, roverall, err_roverall, fig, pc = cf.ratio_2D(
        pions_fake,
        reco_df,
        x_var=x_v,
        y_var=y_v,
        x_label=x_l,
        y_label=y_l,
        cbar_label="Fake Rate",
        bins_x=x_b,
        bins_y=y_b,
        range_x=x_r,
        range_y=y_r,
        cmap="Reds",
        vmin=0,
        vmax=1,
        color_text="white",
        color_text2="black",
        threshold=0.7,
        size_text=14,
        figsize=figsize,
        savefig=savefig,
        figname=f"{sample}/FR",
        savefigerr=savefig,
        errfigname=f"{sample}/err_FR",
        offsetx=0.2,
        offsety=0.2,
        percent=True,
        closefig=False,
    )
    (
        dictionary["FR_overall"],
        dictionary["err_FR_overall"],
        dictionary["FR"],
        dictionary["err_FR"],
    ) = (roverall, err_roverall, r, err_r)
    figs.append(fig)
    data.append([roverall, err_roverall])
    # rows.append('FR')
    rows.append("Fake Rate")

    # clone rate
    print("clone rate")
    x, y, r, err_r, h_n1, h_n2, roverall, err_roverall, fig, pc = cf.ratio_2D(
        pions_clone,
        pions_wRelationToMC,
        x_var=x_v,
        y_var=y_v,
        x_label=x_l,
        y_label=y_l,
        cbar_label="Clone Rate",
        bins_x=x_b,
        bins_y=y_b,
        range_x=x_r,
        range_y=y_r,
        cmap="Blues",
        vmin=0,
        vmax=1,
        color_text="white",
        color_text2="black",
        threshold=0.8,
        size_text=14,
        figsize=figsize,
        savefig=savefig,
        figname=f"{sample}/CR",
        savefigerr=savefig,
        errfigname=f"{sample}/err_CR",
        offsetx=0.2,
        offsety=0.2,
        percent=True,
        closefig=False,
    )
    (
        dictionary["CR_overall"],
        dictionary["err_CR_overall"],
        dictionary["CR"],
        dictionary["err_CR"],
    ) = (roverall, err_roverall, r, err_r)
    figs.append(fig)
    data.append([roverall, err_roverall])
    # rows.append('CR')
    rows.append("Clone Rate")

    # flip right
    print("correctly flipped")
    x, y, r, err_r, h_n1, h_n2, roverall, err_roverall, fig, pc = cf.ratio_2D(
        pions_tigthMatch_flipRefit,
        pions_looseMatch_flipRefit,
        x_var=x_v,
        y_var=y_v,
        x_label=x_l,
        y_label=y_l,
        cbar_label="Flip Right",
        bins_x=x_b,
        bins_y=y_b,
        range_x=x_r,
        range_y=y_r,
        cmap="YlGn",
        vmin=0,
        vmax=1,
        color_text="white",
        color_text2="black",
        threshold=0.5,
        size_text=14,
        figsize=figsize,
        savefig=savefig,
        figname=f"{sample}/FlipR",
        savefigerr=savefig,
        errfigname=f"{sample}/err_FlipR",
        offsetx=0.2,
        offsety=0.2,
        percent=True,
        closefig=False,
    )
    (
        dictionary["FlipR_overall"],
        dictionary["err_FlipR_overall"],
        dictionary["FlipR"],
        dictionary["err_FlipR"],
    ) = (roverall, err_roverall, r, err_r)
    figs.append(fig)
    data.append([roverall, err_roverall])
    # rows.append('FlipR')
    rows.append("Correctly Flipped")

    # flip wrong
    print("wrongly flipped")
    x, y, r, err_r, h_n1, h_n2, roverall, err_roverall, fig, pc = cf.ratio_2D(
        pions_wrongMatch_flipRefit,
        pions_looseMatch_flipRefit,
        x_var=x_v,
        y_var=y_v,
        x_label=x_l,
        y_label=y_l,
        cbar_label="Flip Wrong",
        bins_x=x_b,
        bins_y=y_b,
        range_x=x_r,
        range_y=y_r,
        cmap="Reds",
        vmin=0,
        vmax=1,
        color_text="white",
        color_text2="black",
        threshold=0.6,
        size_text=14,
        figsize=figsize,
        savefig=savefig,
        figname=f"{sample}/FlipW",
        savefigerr=savefig,
        errfigname=f"{sample}/err_FlipW",
        offsetx=0.2,
        offsety=0.2,
        percent=True,
        closefig=False,
    )
    (
        dictionary["FlipW_overall"],
        dictionary["err_FlipW_overall"],
        dictionary["FlipW"],
        dictionary["err_FlipW"],
    ) = (roverall, err_roverall, r, err_r)
    figs.append(fig)
    data.append([roverall, err_roverall])
    # rows.append('FlipW')
    rows.append("Wrongly Flipped")

    # flipping efficiency
    print("flipping efficiency")
    x, y, r, err_r, h_n1, h_n2, roverall, err_roverall, fig, pc = cf.ratio_2D(
        pions_tigthMatch_flipRefit,
        pions_toBeFlipped,
        x_var=x_v,
        y_var=y_v,
        x_label=x_l,
        y_label=y_l,
        cbar_label="Flipping efficiency",
        bins_x=x_b,
        bins_y=y_b,
        range_x=x_r,
        range_y=y_r,
        cmap="YlGn",
        vmin=0,
        vmax=1,
        color_text="white",
        color_text2="black",
        threshold=0.5,
        size_text=14,
        figsize=figsize,
        savefig=savefig,
        figname=f"{sample}/FlipE",
        savefigerr=savefig,
        errfigname=f"{sample}/err_FlipE",
        offsetx=0.2,
        offsety=0.2,
        percent=True,
        closefig=False,
    )
    (
        dictionary["FlipE_overall"],
        dictionary["err_FlipE_overall"],
        dictionary["FlipE"],
        dictionary["err_FlipE"],
    ) = (roverall, err_roverall, r, err_r)
    figs.append(fig)
    data.append([roverall, err_roverall])
    # rows.append('FlipE')
    rows.append("   Flipping efficiency   ")

    # flipped fraction
    print("flipped fraction")
    x, y, r, err_r, h_n1, h_n2, roverall, err_roverall, fig, pc = cf.ratio_2D(
        pions_flipRefit,
        reco_df,
        x_var=x_v,
        y_var=y_v,
        x_label=x_l,
        y_label=y_l,
        cbar_label="Flipped fraction",
        bins_x=x_b,
        bins_y=y_b,
        range_x=x_r,
        range_y=y_r,
        cmap="Blues",
        vmin=0,
        vmax=1,
        color_text="white",
        color_text2="black",
        threshold=0.8,
        size_text=14,
        figsize=figsize,
        savefig=savefig,
        figname=f"{sample}/FlipF",
        savefigerr=savefig,
        errfigname=f"{sample}/err_FlipF",
        offsetx=0.2,
        offsety=0.2,
        percent=True,
        closefig=False,
    )
    (
        dictionary["FlipF_overall"],
        dictionary["err_FlipF_overall"],
        dictionary["FlipF"],
        dictionary["err_FlipF"],
    ) = (roverall, err_roverall, r, err_r)
    figs.append(fig)
    data.append([roverall, err_roverall])
    # rows.append('FlipF')
    rows.append("   Flipped fraction   ")

    # ============================================

    dict_name = f"{sample}/all.pkl"
    with open(dict_name, "wb") as fp:
        pickle.dump(dictionary, fp)

    # ========================================================
    # Table
    colors = plt.cm.BuPu(np.linspace(0, 0.5, len(rows)))
    columns = ("Central value (%)", r"$\sigma$ (%)")
    n_rows = len(data)
    index = np.arange(len(columns)) + 0.3
    y_offset = np.zeros(len(columns))
    cell_text = []

    for row in range(n_rows):
        y_offset = data[row]
        # cell_text.append([x for x in y_offset])
        cell_text.append([f"{x*100:.4f}" for x in y_offset])
    colors = colors[::-1]

    figTable, axT = plt.subplots(figsize=figsize)
    axT.axis("off")
    axT.xaxis.set_visible(False)
    axT.yaxis.set_visible(False)

    the_table = axT.table(
        cellText=cell_text,
        rowLabels=rows,
        rowColours=colors,
        rowLoc="center",
        colLabels=columns,
        colLoc="center",
        loc="center",
        fontsize=25,
        bbox=[0.2, 0.1, 0.85, 0.8],
    )

    figTable.savefig(f"{sample}/OverallTable.png")
    figs.append(figTable)
    # ==============================================================

    return dictionary, figs


def compare_plots(
    dict1, dict2, sample1, sample2, savefig=True, closefig=True, figsize=(14, 10)
):

    dict_keys = [k for k in dict1.keys()]

    fom_keys = []
    for k in dict_keys:
        if ("_overall" not in k) and ("err_" not in k):
            fom_keys.append(k)

    # Remove the first three elements ['sample', 'h_n1', 'h_n2']
    fom_keys = fom_keys[5:]

    fom_difference_list = []
    for k in fom_keys:
        diff = np.subtract(dict1[k], dict2[k])
        fom_difference_list.append(diff)

    folder = f"comparison_{sample1}_{sample2}/"
    if not os.path.exists(folder):
        os.makedirs(folder)

    # common for all plots
    xvariable, yvariable = dict1["xvariable"], dict1["yvariable"]
    xedges, yedges = dict1["xedges"], dict1["yedges"]
    bins_x, bins_y = len(xedges) - 1, len(yedges) - 1
    range_x, range_y = (xedges[0], xedges[-1]), (yedges[0], yedges[-1])
    bin_width_x = [(xedges[i + 1] - xedges[i]) for i in range(bins_x)]
    x_val = [(xedges[i] + bin_width_x[i] / 2) for i in range(bins_x)]
    bin_width_y = [(yedges[i + 1] - yedges[i]) for i in range(bins_y)]
    y_val = [(yedges[i] + bin_width_y[i] / 2) for i in range(bins_y)]
    x_l, y_l = r"cos$\theta$", "p$_{t}$ [GeV/c]"
    z_label = f"{sample1} - {sample2}"

    offsetx, offsety = 0.2, 0.2
    size_text = 14
    color_text = "black"

    figs = []
    for i_f, FOM in enumerate(fom_keys):

        diff = fom_difference_list[i_f]
        fig, ax = plt.subplots(figsize=figsize)

        cmap = "RdYlGn"
        if ("CA" in FOM) or ("FR" in FOM) or ("CR" in FOM):
            cmap = "RdYlGn_r"

        pc = ax.pcolorfast(
            xedges,
            yedges,
            diff.T,
            cmap=cmap,
            vmin=-0.2,
            vmax=0.2,
        )

        if not savefig:
            plt.title(FOM)

        ax.set_xlabel(x_l, fontsize=20)
        ax.set_ylabel(y_l, fontsize=20)

        plt.xticks(fontsize=16)
        plt.yticks(fontsize=16)

        # Create colorbar
        cax = fig.add_axes(
            [
                ax.get_position().x1 + 0.01,
                ax.get_position().y0,
                0.02,
                ax.get_position().height,
            ]
        )
        cbar = ax.figure.colorbar(pc, ax=ax, cax=cax)
        cbar.ax.set_ylabel(z_label, va="bottom", fontsize=20, labelpad=25, rotation=270)

        if size_text != None:
            texts = []
            for i in range(diff.shape[0]):
                for j in range(diff.shape[1]):
                    bw_x = bin_width_x[i]
                    bw_y = bin_width_y[j]

                    value = diff[i, j]
                    valuepercent = value * 100
                    s_text = f"{valuepercent:.4f} %"

                    if math.isnan(value):
                        s_text = ""
                    xtxt = x_val[i] - (offsetx * bw_x)
                    ytxt = y_val[j] - (offsety * bw_y)
                    text = pc.axes.text(
                        xtxt, ytxt, s_text, color=color_text, fontsize=size_text
                    )

        plt.yticks(fontsize=16)

        figs.append(fig)

        if savefig:
            figname = folder + FOM + ".png"
            print("Saving ", figname)
            plt.savefig(figname)

        if closefig:
            plt.close(figname)

    return figs, fom_keys


def createPDF(figs, namePDF, sample, titles=None):
    with PdfPages(namePDF) as pdf:
        for i, fig in enumerate(figs):
            fig.suptitle(sample, fontsize=16)
            if titles:
                fig.get_axes()[0].set_title(titles[i], fontsize=25)
                # fig.suptitle('This is a somewhat long figure title', fontsize=16)
            pdf.savefig(fig)
            plt.close()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-f1", "--file1", required=True, help="First root file to be analysed"
    )
    parser.add_argument(
        "-p1",
        "--prefix1",
        type=str,
        required=True,
        help="Prefix for output files and sample label",
    )
    parser.add_argument(
        "-f2",
        "--file2",
        type=str,
        required=False,
        help="Second root file to be analysed.",
    )
    parser.add_argument(
        "-p2",
        "--prefix2",
        type=str,
        required=("--file2" in sys.argv),
        help="Prefix for second root file",
    )
    return parser.parse_args()


def main(args):

    seen, savefig = True, True
    figsize = (14, 10)

    print("Analysing sample:", args.prefix1)
    dict1, figs1 = plots(
        rootfile=args.file1,
        sample=args.prefix1,
        seen=seen,
        savefig=savefig,
        figsize=figsize,
    )

    createPDF(figs1, f"{args.prefix1}/all.pdf", sample=args.prefix1)

    if args.file2:
        print("\nAnalysing second sample:", args.prefix2)
        dict2, figs2 = plots(
            rootfile=args.file2,
            sample=args.prefix2,
            seen=seen,
            savefig=savefig,
            figsize=figsize,
        )
        createPDF(figs2, f"{args.prefix2}/all.pdf", sample=args.prefix2)

        print("\nPreparing comparison")
        figs, titles = compare_plots(dict1, dict2, args.prefix, args.sample2)
        createPDF(
            figs,
            f"{args.prefix}_VS_{args.sample2}.pdf",
            sample=f"{args.prefix} VS {args.sample2}",
            titles=titles,
        )


if __name__ == "__main__":
    args = parse_args()
    main(args)
