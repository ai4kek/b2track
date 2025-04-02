#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

import math
import time

import matplotlib.pyplot as plt
import numpy
import numpy as np
import pandas as pd
import pylab as pl
import scipy.special
from matplotlib import rc
from matplotlib.colors import LogNorm
from matplotlib.pyplot import *
from scipy.integrate import quad

# ====================================================================================================


def scalar_product(x1, y1, z1, x2, y2, z2):
    return x1 * x2 + y1 * y2 + z1 * z2


def p(px, py, pz):
    return np.sqrt(px**2 + py**2 + pz**2)


def pt(px, py):
    return np.sqrt(px**2 + py**2)


def costheta(px, py, pz):
    return pz / p(px, py, pz)


def phi(px, py):
    return np.arctan2(py, px)


def costheta_between_momenta(px1, py1, pz1, px2, py2, pz2):
    return scalar_product(px1, py1, pz1, px2, py2, pz2) / (
        p(px1, py1, pz1) * p(px2, py2, pz2)
    )


# ====================================================================================================

# ## 2D


# Functions to plot 2D ratios
def ratio_2D(
    numerator,
    denominator,
    x_var="mcCosTheta",
    y_var="mcP",
    x_label=None,
    y_label=None,
    cbar_label="Efficiency",
    bins_x=2,
    bins_y=5,
    range_x=(-1, 1),
    range_y=(0, 1),
    figsize=(12, 12),
    cmap="YlGn",
    vmin=0,
    vmax=1,
    vminErr=0,
    vmaxErr=0.02,
    color_text="black",
    color_text2="black",
    threshold=0.5,
    size_text=16,
    offsetx=0.2,
    offsety=0.2,
    plotRatioErr=True,
    noNaNallowed=False,
    percent=False,
    moreDigits=False,
    showOnlyGoodValues=True,
    limitValue=0.2,
    savefig=False,
    figname="test.png",
    savefigerr=False,
    errfigname="errtest.png",
    closefig=False,
):

    if type(bins_x) is int:
        bin_width_x = (range_x[1] - range_x[0]) / bins_x
        x_val = [
            range_x[0] + ii * bin_width_x + (bin_width_x) / 2.0 for ii in range(bins_x)
        ]
    else:
        bin_width_x = [(bins_x[i + 1] - bins_x[i]) for i in range(len(bins_x) - 1)]
        x_val = [(bins_x[i] + bin_width_x[i] / 2) for i in range(len(bins_x) - 1)]
        # print('# x val', len(x_val), '\t # edges: ', len(binx_x))

    if type(bins_y) is int:
        bin_width_y = (range_y[1] - range_y[0]) / bins_y
        y_val = [
            range_y[0] + ii * bin_width_y + (bin_width_y) / 2.0 for ii in range(bins_y)
        ]
    else:
        bin_width_y = [(bins_y[i + 1] - bins_y[i]) for i in range(len(bins_y) - 1)]
        y_val = [(bins_y[i] + bin_width_y[i] / 2) for i in range(len(bins_y) - 1)]

    xlbl, ylbl = x_label, y_label
    if xlbl == None:
        xlbl = x_var
    if ylbl == None:
        ylbl = y_var

    # Evalute the overall value with error
    ratio_overall, err_ratio_overall = -1.0, -1.0

    if len(denominator[x_var]) > 0:
        ratio_overall = len(numerator[x_var]) / len(denominator[x_var])
        err_ratio_overall = np.sqrt((ratio_overall * (1 - ratio_overall))) / np.sqrt(
            len(denominator[x_var])
        )
    print("ratio (overall):", f"{ratio_overall:.6f} +- {err_ratio_overall:.6f}")

    fig, ax = plt.subplots(1, 2, figsize=(12, 6))
    # hist2d of the numerator
    h_num = ax[0].hist2d(
        numerator[x_var],
        numerator[y_var],
        range=[range_x, range_y],
        bins=[bins_x, bins_y],
        cmin=1,
    )
    ax[0].set_title("Numerator")
    ax[0].set_xlabel(xlbl)
    ax[0].set_ylabel(ylbl)

    # hist2d of the denominator
    h_den = ax[1].hist2d(
        denominator[x_var],
        denominator[y_var],
        range=[range_x, range_y],
        bins=[bins_x, bins_y],
        cmin=1,
    )
    ax[1].set_title("Denominator")
    ax[1].set_xlabel(xlbl)
    ax[1].set_ylabel(ylbl)

    if noNaNallowed:
        # Replacing nan with 0
        h_num[0][np.isnan(h_num[0])] = 0
        h_den[0][np.isnan(h_den[0])] = 0

    ratio = np.divide(h_num[0], h_den[0])

    # ratio error obtained manipulating matrices
    rM1 = 1 - ratio
    err_ratio = np.multiply(ratio, rM1)
    err_ratio = np.divide(err_ratio, h_den[0])
    err_ratio = np.sqrt(err_ratio)

    # debug: look for values of the ratio > 1
    for i in range(ratio.shape[0]):
        for j in range(ratio.shape[1]):
            if ratio[i][j] > 1.0:
                print("Something might be wrong! The ratio is > 1! Please double-chek!")
                print(i, ", ", j, ", r:", ratio[i][j])
                print("n:", h_num[0][i][j], "\t d:", h_den[0][i][j])

    close(fig)

    # ==========
    # plot ratio

    fig, ax = plt.subplots(figsize=figsize)

    pc = ax.pcolorfast(
        h_num[1], h_num[2], ratio.T, cmap=cmap, vmin=vmin, vmax=vmax
    )  # , ratio.T)
    ax.set_xlabel(xlbl, fontsize=20)
    ax.set_ylabel(ylbl, fontsize=20)
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
    cbar.ax.set_ylabel(cbar_label, va="bottom", fontsize=20, labelpad=25)

    if size_text != None:
        texts = []
        for i in range(ratio.shape[0]):
            for j in range(ratio.shape[1]):

                bw_x, bw_y = 1.0, 1.0

                if type(bins_x) is int:
                    bw_x = bin_width_x
                else:
                    bw_x = bin_width_x[i]

                if type(bins_y) is int:
                    bw_y = bin_width_y
                else:
                    bw_y = bin_width_y[j]

                s_text = f"{ratio[i,j]:.4f}"
                if moreDigits:
                    s_text = f"{ratio[i,j]:.6f}"
                if percent:
                    s_text = f"{ratio[i,j]*100:.2f} %"
                    if moreDigits:
                        s_text = f"{ratio[i,j]*100:.3f} %"

                if showOnlyGoodValues:
                    if err_ratio[i, j] > limitValue or err_ratio[i, j] == 0:
                        s_text = ""
                if math.isnan(ratio[i, j]):
                    s_text = ""

                colort = color_text
                if ratio[i, j] < threshold:
                    colort = color_text2

                xtxt = x_val[i] - (offsetx * bw_x)
                ytxt = y_val[j] - (offsety * bw_y)

                text = pc.axes.text(
                    xtxt, ytxt, s_text, color=colort, fontsize=size_text
                )

    plt.yticks(fontsize=16)

    if savefig:
        fig.savefig(figname)
    if closefig:
        close(fig)

    # ==========
    # plot error ratio

    if plotRatioErr:
        figE, axE = plt.subplots(figsize=figsize)

        pc2 = axE.pcolorfast(
            h_num[1], h_num[2], err_ratio.T, cmap="binary", vmin=vminErr, vmax=vmaxErr
        )
        axE.set_xlabel(xlbl, fontsize=20)
        axE.set_ylabel(ylbl, fontsize=20)
        plt.xticks(fontsize=16)
        plt.yticks(fontsize=16)

        # Create colorbar
        cax = figE.add_axes(
            [
                axE.get_position().x1 + 0.01,
                axE.get_position().y0,
                0.02,
                axE.get_position().height,
            ]
        )
        cbar = axE.figure.colorbar(pc2, ax=axE, cax=cax)
        cbar.ax.set_ylabel("Error " + cbar_label, va="bottom", fontsize=20, labelpad=25)
        if size_text != None:
            texts = []
            c_text = "darkcyan"
            for i in range(err_ratio.shape[0]):
                for j in range(err_ratio.shape[1]):
                    bw_x, bw_y = 1.0, 1.0

                    if type(bins_x) is int:
                        bw_x = bin_width_x
                    else:
                        bw_x = bin_width_x[i]

                    if type(bins_y) is int:
                        bw_y = bin_width_y
                    else:
                        bw_y = bin_width_y[j]

                    s_text = f"{err_ratio[i,j]:.4f}"
                    if moreDigits:
                        s_text = f"{err_ratio[i,j]:.6f}"
                    if percent:
                        s_text = f"{err_ratio[i,j]*100:.2f} %"
                        if moreDigits:
                            s_text = f"{err_ratio[i,j]*100:.3f} %"

                    if showOnlyGoodValues:
                        if err_ratio[i, j] > limitValue or err_ratio[i, j] == 0:
                            s_text = ""
                    if math.isnan(err_ratio[i, j]):
                        s_text = ""

                    text = pc2.axes.text(
                        x_val[i] - (offsetx * bw_x),
                        y_val[j] - (offsety * bw_y),
                        s_text,
                        color=c_text,
                        fontsize=size_text,
                    )

        plt.yticks(fontsize=16)
        if savefigerr:
            figE.savefig(errfigname)
        # if closefig:
        close(figE)

    return (
        x_val,
        y_val,
        ratio,
        err_ratio,
        h_num[1],
        h_num[2],
        ratio_overall,
        err_ratio_overall,
        fig,
        pc,
    )


# Functions to plot charge asymmetry
def chargeasym_2D(
    tightMatch_plus,
    tightMatch_minus,
    x_var="mcCosTheta",
    y_var="mcP",
    x_label=None,
    y_label=None,
    cbar_label="Charge asymmetry",
    bins_x=2,
    bins_y=5,
    range_x=(-1, 1),
    range_y=(0, 1),
    figsize=(12, 12),
    cmap="seismic_r",
    vmin=-2,
    vmax=2,
    vminErr=0,
    vmaxErr=0.02,
    color_text="black",
    color_text2="black",
    threshold=0.5,
    size_text=16,
    offsetx=0.2,
    offsety=0.2,
    plotRatioErr=True,
    noNaNallowed=False,
    percent=False,
    moreDigits=False,
    showOnlyGoodValues=True,
    limitValue=0.2,
    savefig=False,
    figname="test.png",
    savefigerr=False,
    errfigname="errtest.png",
    closefig=False,
):
    """

    charge asymmetry (# tight match plus - # tight matches minus) / (# tight match plus + # tight matches minus)

    """

    if type(bins_x) is int:
        bin_width_x = (range_x[1] - range_x[0]) / bins_x
        x_val = [
            range_x[0] + ii * bin_width_x + (bin_width_x) / 2.0 for ii in range(bins_x)
        ]
    else:
        bin_width_x = [(bins_x[i + 1] - bins_x[i]) for i in range(len(bins_x) - 1)]
        x_val = [(bins_x[i] + bin_width_x[i] / 2) for i in range(len(bins_x) - 1)]

    if type(bins_y) is int:
        bin_width_y = (range_y[1] - range_y[0]) / bins_y
        y_val = [
            range_y[0] + ii * bin_width_y + (bin_width_y) / 2.0 for ii in range(bins_y)
        ]
    else:
        bin_width_y = [(bins_y[i + 1] - bins_y[i]) for i in range(len(bins_y) - 1)]
        y_val = [(bins_y[i] + bin_width_y[i] / 2) for i in range(len(bins_y) - 1)]

    xlbl, ylbl = x_label, y_label
    if xlbl == None:
        xlbl = x_var
    if ylbl == None:
        ylbl = y_var

    # Evalute the overall value with error
    Nplus, Nminus = len(tightMatch_plus[x_var]), len(tightMatch_minus[x_var])
    ratio_overall = (Nplus - Nminus) / (Nplus + Nminus)
    err_ratio_overall = np.sqrt((4 * Nplus * Nminus) / ((Nplus + Nminus) ** 3))

    print(
        "Charge asymmetry (overall):", f"{ratio_overall:.6f} +- {err_ratio_overall:.6f}"
    )

    fig, ax = plt.subplots(1, 2, figsize=(12, 6))
    # tight match plus
    h_tm_plus = ax[0].hist2d(
        tightMatch_plus[x_var],
        tightMatch_plus[y_var],
        range=[range_x, range_y],
        bins=[bins_x, bins_y],
        cmin=1,
    )
    ax[0].set_title("Tight match + ")
    ax[0].set_xlabel(xlbl)
    ax[0].set_ylabel(ylbl)

    # tight match minus
    h_tm_minus = ax[1].hist2d(
        tightMatch_minus[x_var],
        tightMatch_minus[y_var],
        range=[range_x, range_y],
        bins=[bins_x, bins_y],
        cmin=1,
    )
    ax[1].set_title("Tight match - ")
    ax[1].set_xlabel(xlbl)
    ax[1].set_ylabel(ylbl)

    # ==========
    if noNaNallowed:
        # Replacing nan with 0
        h_tm_plus[0][np.isnan(h_tm_plus[0])] = 0
        h_tm_minus[0][np.isnan(h_tm_minus[0])] = 0

    # numerator: difference
    h_num = h_tm_plus[0] - h_tm_minus[0]
    # denominator: sum
    h_den = h_tm_plus[0] + h_tm_minus[0]

    ratio = np.divide(h_num, h_den)

    # variance = (4*N+*N-)/N^3, where N = N+ + N-
    # http://blast.lns.mit.edu/BlastTalk/archive/att-5707/01-asymmetry_calculations.pdf
    err2_ratio_num = np.multiply(h_tm_plus[0], h_tm_minus[0])
    err2_ratio_num = np.multiply(4, err2_ratio_num)
    err2_ratio_den = np.multiply(h_den, h_den)
    err2_ratio_den = np.multiply(err2_ratio_den, h_den)
    err2_ratio = np.divide(err2_ratio_num, err2_ratio_den)
    err_ratio = np.sqrt(err2_ratio)

    # debug: look for values of the ratio > 1
    for i in range(ratio.shape[0]):
        for j in range(ratio.shape[1]):
            if ratio[i][j] > 1.0:
                print("Something might be wrong! The ratio is > 1! Please double-chek!")
                print(
                    i, ", ", j, ", r:", ratio[i][j]
                )  # , '\t n:', numerator[i][j], '\t d:', denominator[i][j])
                print("n:", h_num[0][i][j], "\t d:", h_den[i][j])
    close(fig)

    # ==========
    # plot ratio

    fig, ax = plt.subplots(figsize=figsize)

    pc = ax.pcolorfast(
        h_tm_plus[1], h_tm_plus[2], ratio.T, cmap=cmap, vmin=vmin, vmax=vmax
    )
    ax.set_xlabel(xlbl, fontsize=20)
    ax.set_ylabel(ylbl, fontsize=20)
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
    cbar.ax.set_ylabel(cbar_label, va="bottom", fontsize=20, labelpad=25)

    if color_text != None:
        texts = []
        for i in range(ratio.shape[0]):
            for j in range(ratio.shape[1]):

                bw_x, bw_y = 1.0, 1.0

                if type(bins_x) is int:
                    bw_x = bin_width_x
                else:
                    bw_x = bin_width_x[i]

                if type(bins_y) is int:
                    bw_y = bin_width_y
                else:
                    bw_y = bin_width_y[j]

                s_text = f"{ratio[i,j]:.4f}"
                if moreDigits:
                    s_text = f"{ratio[i,j]:.6f}"

                if percent:
                    s_text = f"{ratio[i,j]*100:.2f} %"
                    if moreDigits:
                        s_text = f"{ratio[i,j]*100:.3f} %"

                if showOnlyGoodValues:
                    if err_ratio[i, j] > limitValue or err_ratio[i, j] == 0:
                        s_text = ""
                if math.isnan(ratio[i, j]):
                    s_text = ""

                colort = color_text
                if ratio[i, j] < threshold:
                    colort = color_text2

                xtxt = x_val[i] - (offsetx * bw_x)
                ytxt = y_val[j] - (offsety * bw_y)

                text = pc.axes.text(
                    xtxt, ytxt, s_text, color=colort, fontsize=size_text
                )

    plt.yticks(fontsize=16)
    if savefig:
        fig.savefig(figname)
    if closefig:
        close(fig)

    # ==========
    # plot error ratio

    if plotRatioErr:
        figE, axE = plt.subplots(figsize=figsize)

        pc2 = axE.pcolorfast(
            h_tm_plus[1],
            h_tm_plus[2],
            err_ratio.T,
            cmap="binary",
            vmin=vminErr,
            vmax=vmaxErr,
        )
        axE.set_xlabel(xlbl, fontsize=20)
        axE.set_ylabel(ylbl, fontsize=20)
        plt.xticks(fontsize=16)
        plt.yticks(fontsize=16)

        # Create colorbar
        cax = figE.add_axes(
            [
                axE.get_position().x1 + 0.01,
                axE.get_position().y0,
                0.02,
                axE.get_position().height,
            ]
        )
        cbar = axE.figure.colorbar(pc2, ax=axE, cax=cax)
        cbar.ax.set_ylabel("Error " + cbar_label, va="bottom", fontsize=20, labelpad=25)

        if color_text != None:
            texts = []
            c_text = "darkcyan"
            for i in range(err_ratio.shape[0]):
                for j in range(err_ratio.shape[1]):

                    bw_x, bw_y = 1.0, 1.0

                    if type(bins_x) is int:
                        bw_x = bin_width_x
                    else:
                        bw_x = bin_width_x[i]

                    if type(bins_y) is int:
                        bw_y = bin_width_y
                    else:
                        bw_y = bin_width_y[j]

                    s_text = f"{err_ratio[i,j]:.4f}"
                    if moreDigits:
                        s_text = f"{err_ratio[i,j]:.6f}"
                    if percent:
                        s_text = f"{err_ratio[i,j]*100:.2f} %"
                        if moreDigits:
                            s_text = f"{err_ratio[i,j]*100:.3f} %"

                    if showOnlyGoodValues:
                        if err_ratio[i, j] > limitValue or err_ratio[i, j] == 0:
                            s_text = ""

                    if math.isnan(err_ratio[i, j]):
                        s_text = ""

                    xtxt = x_val[i] - (offsetx * bw_x)
                    ytxt = y_val[j] - (offsety * bw_y)

                    text = pc2.axes.text(
                        xtxt, ytxt, s_text, color=colort, fontsize=size_text
                    )

        plt.yticks(fontsize=16)
        if savefigerr:
            figE.savefig(errfigname)
        # if closefig:
        close(figE)

    return (
        x_val,
        y_val,
        ratio,
        err_ratio,
        h_num[1],
        h_num[2],
        ratio_overall,
        err_ratio_overall,
        fig,
        pc,
    )


# Functions to plot 2D ratios
def normalized_2D(
    variable,
    x_var="mcCosTheta",
    y_var="mcP",
    x_label=None,
    y_label=None,
    cbar_label="Fraction of MCParticles",
    bins_x=2,
    bins_y=5,
    range_x=(-1, 1),
    range_y=(0, 1),
    figsize=(12, 12),
    cmap="viridis",
    vmin=0,
    vmax=1,
    percent=False,
    minN=10,
    debug=False,
    moreDigits=False,
    color_text="white",
    size_text=None,
    color_text2="black",
    threshold=1,
    offsetx=0.2,
    offsety=0.2,
    plotRatioErr=True,
    noNaNallowed=False,
    savefig=False,
    figname="test.png",
    fignamefrac="testfrac.png",
    closefig=False,
):

    if type(bins_x) is int:
        bin_width_x = (range_x[1] - range_x[0]) / bins_x
        x_val = [
            range_x[0] + ii * bin_width_x + (bin_width_x) / 2.0 for ii in range(bins_x)
        ]
    else:
        bin_width_x = [(bins_x[i + 1] - bins_x[i]) for i in range(len(bins_x) - 1)]
        x_val = [(bins_x[i] + bin_width_x[i] / 2) for i in range(len(bins_x) - 1)]

    if type(bins_y) is int:
        bin_width_y = (range_y[1] - range_y[0]) / bins_y
        y_val = [
            range_y[0] + ii * bin_width_y + (bin_width_y) / 2.0 for ii in range(bins_y)
        ]
    else:
        bin_width_y = [(bins_y[i + 1] - bins_y[i]) for i in range(len(bins_y) - 1)]
        y_val = [(bins_y[i] + bin_width_y[i] / 2) for i in range(len(bins_y) - 1)]

    xlbl, ylbl = x_label, y_label
    if xlbl == None:
        xlbl = x_var
    if ylbl == None:
        ylbl = y_var

    nEntries = len(variable[x_var])
    s_plotlim = (
        "(" + x_var + ">" + str(range_x[0]) + " and " + x_var + "<" + str(range_x[1])
    )
    s_plotlim += (
        " and "
        + y_var
        + ">"
        + str(range_y[0])
        + " and "
        + y_var
        + "<"
        + str(range_y[1])
        + ")"
    )
    if debug:
        print(s_plotlim)

    var_inPlot = variable.query(s_plotlim)
    nEntries_inPlot = len(var_inPlot[x_var])

    print("# entries:", nEntries, "\t # entries in plot range:", nEntries_inPlot)
    print("Fraction pions in plot range:", nEntries_inPlot / nEntries * 100, " %")
    print(
        "Fraction pions outside plot range:",
        (1 - (nEntries_inPlot / nEntries)) * 100,
        " %\n",
    )

    fig1, ax = plt.subplots(figsize=figsize)

    h = ax.hist2d(
        variable[x_var],
        variable[y_var],
        range=[range_x, range_y],
        bins=[bins_x, bins_y],
        cmin=minN,
        norm=matplotlib.colors.LogNorm(),
    )

    ax.set_xlabel(xlbl, fontsize=20)
    ax.set_ylabel(ylbl, fontsize=20)

    # Create colorbar
    cax = fig1.add_axes(
        [
            ax.get_position().x1 + 0.01,
            ax.get_position().y0,
            0.02,
            ax.get_position().height,
        ]
    )
    cbar = ax.figure.colorbar(h[3], ax=ax, cax=cax)
    cbar.ax.set_ylabel("Entries", va="bottom", fontsize=20, labelpad=25)

    plt.yticks(fontsize=16)

    # ===========================

    fraction = np.divide(h[0], nEntries)

    # plot ratio

    fig, ax = plt.subplots(figsize=figsize)

    pc = ax.pcolorfast(
        h[1], h[2], fraction.T, cmap=cmap, vmin=vmin, vmax=vmax
    )  # , ratio.T)
    ax.set_xlabel(xlbl, fontsize=20)
    ax.set_ylabel(ylbl, fontsize=20)
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
    cbar.ax.set_ylabel(cbar_label, va="bottom", fontsize=20, labelpad=25)

    if size_text != None:
        texts = []
        for i in range(fraction.shape[0]):
            for j in range(fraction.shape[1]):

                bw_x, bw_y = 1.0, 1.0

                if type(bins_x) is int:
                    bw_x = bin_width_x
                else:
                    bw_x = bin_width_x[i]

                if type(bins_y) is int:
                    bw_y = bin_width_y
                else:
                    bw_y = bin_width_y[j]

                s_text = f"{fraction[i,j]:.4f}"
                if moreDigits:
                    s_text = f"{fraction[i,j]:.6f}"
                if percent:
                    s_text = f"{fraction[i,j]*100:.2f} %"
                    if moreDigits:
                        s_text = f"{fraction[i,j]*100:.3f} %"
                if math.isnan(fraction[i, j]):
                    s_text = ""

                colort = color_text
                if fraction[i, j] > threshold:
                    colort = color_text2
                xtxt = x_val[i] - (offsetx * bw_x)
                ytxt = y_val[j] - (offsety * bw_y)
                text = pc.axes.text(
                    xtxt, ytxt, s_text, color=colort, fontsize=size_text
                )

    if savefig:
        fig.savefig(fignamefrac)
        fig1.savefig(figname)

    if closefig:
        close(fig)
        close(fig1)

    return x_val, y_val, h[1], h[2], nEntries, fig1, fig


### 1D


def ratio_1D(
    numerator,
    denominator,
    var="mcCosTheta",
    x_label=None,
    y_label="Efficiency",
    bns=100,
    rng=(0.0, 1),
    clr="tab:blue",
    ylim=(0.8, 1.02),
    figsize=(12, 10),
    savefig=False,
    figname="prova.png",
):

    fig, ax = plt.subplots(figsize=figsize)

    hwb = (rng[1] - rng[0]) / (2 * bns)

    # denominator
    a0, b0, c0 = plt.hist(denominator[var], bins=bns, range=rng)

    # numerator
    a1, b1, c1 = plt.hist(numerator[var], bins=bns, range=rng)

    xval = np.array([b + hwb for b in b0[:-1]])
    ratio = np.array([a1[i] / a0[i] for i in range(len(a0))])
    err_ratio = np.array(
        [np.sqrt(ratio[i] * (1 - ratio[i])) / np.sqrt(a0[i]) for i in range(len(a0))]
    )

    plt.clf()

    plt.fill_between(xval, ratio - err_ratio, ratio + err_ratio, color=clr, alpha=0.3)
    plt.plot(xval, ratio, "o-", color=clr)  # , linewidth=5)

    # ax.set_xlabel(x_label, fontsize=20)
    # ax.set_ylabel(y_label, fontsize=20)
    plt.xlabel(x_label, fontsize=20)
    plt.ylabel(y_label, fontsize=20)

    plt.xticks(fontsize=16)
    plt.yticks(fontsize=16)

    plt.xlim(rng)
    plt.ylim(ylim)
    plt.gca().yaxis.set_major_locator(MaxNLocator(prune="lower"))

    plt.show()

    if savefig:
        fig.savefig(figname)

    return xval, ratio, err_ratio, fig, ax


def compare_ratio1D(
    xval,
    ratio=[],
    err_ratio=[],
    x_label=None,
    y_label="Efficiency",
    color_list=[],
    label_list=None,
    xlim=None,
    ylim=(0.8, 1.02),
    figsize=(12, 10),
    loc="upper right",
    savefig=False,
    figname="prova.png",
):

    if len(ratio) < 2:
        print("Need a list of ratios to be compared. Please check.")
        return 1
    if (len(ratio) != len(err_ratio)) or (len(ratio) != len(color_list)):
        print("Something wrong with list lenght. Please check.")
        return 1

    fig, ax = plt.subplots(figsize=figsize)

    for i, r in enumerate(ratio):

        plt.fill_between(
            xval, r - err_ratio[i], r + err_ratio[i], color=color_list[i], alpha=0.3
        )
        if label_list != None:
            plt.plot(xval, r, "o-", color=color_list[i], label=label_list[i])
        else:
            plt.plot(xval, r, "o-", color=color_list[i])

    plt.xlabel(x_label, fontsize=20)
    plt.ylabel(y_label, fontsize=20)

    plt.xticks(fontsize=16)
    plt.yticks(fontsize=16)

    if xlim != None:
        plt.xlim(rng)
    if ylim != None:
        plt.ylim(ylim)

    plt.gca().yaxis.set_major_locator(MaxNLocator(prune="lower"))

    if label_list != None:
        plt.legend(loc=loc, fontsize=20)

    if savefig:
        fig.savefig(figname)

    plt.show()
