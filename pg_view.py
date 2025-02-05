#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

###############################################################################
# A more complex python module using matlotlib to create
# advanced plots.
# It gathers the x/y position off all CDCSimHits and draws them in different
# colours depending on associated MCParticle.
###############################################################################

import os
import basf2 as b2
import simulation as si
from ROOT import Belle2
import matplotlib.pyplot as plt
import matplotlib.cm as colormap
from matplotlib.patches import Circle


def SVDPlot(x, y, col, show=0):
    """
    Plot a list of x/y values, plus CDC superlayer boundaries.

    Returns a pyplot.figure that can be saved.
    """
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111)

    # SVD Layout
    layers = [3.9, 8.0, 10.4, 13.5]
    Circs = [Circle((0, 0), a, facecolor="none", edgecolor="lightgrey") for a in layers]
    for e in Circs:
        ax.add_artist(e)

    # Draw the x/y arrays. Note that looping over the hits
    # and drawing them individually would be much slower.
    for i in range(len(col)):
        ax.plot(x[i], y[i], marker=".", color=col[i], linestyle="None", markersize=1)

    # Axis Params
    ax.set_title("SVDSimHits")
    ax.set_xlabel("x [cm]", fontsize=15)
    ax.set_ylabel("y [cm]", fontsize=15)
    ax.set_xlim(-14, 14)
    ax.set_ylim(-14, 14)
    ax.set_aspect("equal")
    ax.grid(False)

    # Fig Params
    fig.tight_layout()
    if show:
        plt.show()
    return fig


def CDCPlot(x, y, col, show=0):
    """
    Plot a list of x/y values, plus CDC superlayer boundaries.

    Returns a pyplot.figure that can be saved.
    """
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111)

    # draw the x/y arrays. note that looping over the hits and
    # drawing them individually would be much slower
    for i in range(len(col)):
        ax.plot(x[i], y[i], marker=".", color=col[i], linestyle="None", markersize=1)

    ax.set_title("CDCSimHits")
    ax.set_xlabel("x [cm]")
    ax.set_ylabel("y [cm]")
    ax.axis("scaled")  # equal scaling and auto-adjusts

    # draw CDC superlayer boundaries
    layers = [16.8, 25.7, 36.5, 47.6, 58.4, 69.5, 80.2, 91.3, 102.0, 111.1]
    Circs = [Circle((0, 0), a, facecolor="none", edgecolor="lightgrey") for a in layers]
    for e in Circs:
        ax.add_artist(e)

    ax.set_xlim(-115, 115)
    ax.set_ylim(-115, 115)
    fig.tight_layout()
    if show:
        plt.show()
    return fig


class SVDPlotModule(b2.Module):
    """An example python module.

    It gathers the x/y position off all SVDSimHits and draws them using
    matplotlib. The result is saved as a PNG.
    """

    #: event counter
    num_events = 0

    def event(self):
        """reimplementation of Module::event().

        loops over the SVDSimHits in the current event.
        """
        svdSimHits = Belle2.PyStoreArray("SVDSimHits")

        # list of lists of simhit positions, one list per mcpart
        trackhits_x = []
        trackhits_y = []

        mcparts = []
        for hit in svdSimHits:
            mcpart = hit.getRelatedFrom("MCParticles")
            if not mcpart:
                continue
            if mcpart not in mcparts:
                mcparts.append(mcpart)
                trackhits_x.append([])
                trackhits_y.append([])
            # add simhit to the list corresponding to this particle
            idx = mcparts.index(mcpart)
            hitpos = hit.getPosIn()  # TVector3

            # TODO: hitpos are in local coordinates, convert to global

            trackhits_x[idx].append(hitpos.X())
            trackhits_y[idx].append(hitpos.Y())

        npart = len(mcparts)
        if npart > 0:
            # plot the (x,y) list on a matplotlib figure
            col = [colormap.jet(1.0 * c / (npart - 1)) for c in range(npart)]
            fig = SVDPlot(trackhits_x, trackhits_y, col)

            filename = f"svdhits_{self.num_events}.png"
            if os.path.lexists(filename):
                b2.B2WARNING(filename + " exists, overwriting ...")
            else:
                b2.B2INFO("creating " + filename + " ...")
            fig.savefig(filename)

        self.num_events += 1

    def terminate(self):
        """reimplementation of Module::terminate()."""
        b2.B2INFO("terminating SVDPlotModule")


class CDCPlotModule(b2.Module):
    """An example python module.

    It gathers the x/y position off all CDCSimHits and draws them using
    matplotlib. The result is saved as a PNG.
    """

    #: event counter
    num_events = 0

    def event(self):
        """reimplementation of Module::event().

        loops over the CDCSimHits in the current event.
        """
        cdcSimHits = Belle2.PyStoreArray("CDCSimHits")

        # list of lists of simhit positions, one list per mcpart
        trackhits_x = []
        trackhits_y = []

        mcparts = []
        for hit in cdcSimHits:
            mcpart = hit.getRelatedFrom("MCParticles")
            if mcpart not in mcparts:
                mcparts.append(mcpart)
                trackhits_x.append([])
                trackhits_y.append([])
            # add simhit to the list corresponding to this particle
            idx = mcparts.index(mcpart)
            hitpos = hit.getPosWire()  # TVector3
            trackhits_x[idx].append(hitpos.X())
            trackhits_y[idx].append(hitpos.Y())

        npart = len(mcparts)
        if npart > 0:
            # plot the (x,y) list on a matplotlib figure
            col = [colormap.jet(1.0 * c / (npart - 1)) for c in range(npart)]
            fig = CDCPlot(trackhits_x, trackhits_y, col)

            filename = f"cdchits_{self.num_events}.png"
            if os.path.lexists(filename):
                b2.B2WARNING(filename + " exists, overwriting ...")
            else:
                b2.B2INFO("creating " + filename + " ...")
            fig.savefig(filename)

        self.num_events += 1

    def terminate(self):
        """reimplementation of Module::terminate()."""
        b2.B2INFO("terminating CDCPlotModule")


# Normal steering file part begins here

# choose the particles you want to simulate
param_pGun = {
    "pdgCodes": [13, -13],
    "nTracks": 6,
    "varyNTracks": 0,
    "momentumGeneration": "uniform",
    "momentumParams": [0.4, 1.6],
    "thetaGeneration": "uniform",
    "thetaParams": [60.0, 120.0],
    "phiGeneration": "uniform",
    "phiParams": [0, 360],
    "vertexGeneration": "uniform",
    "xVertexParams": [0.0, 0.0],
    "yVertexParams": [0.0, 0.0],
    "zVertexParams": [0.0, 0.0],
}

# Create main path
main = b2.Path()
main.add_module("EventInfoSetter", evtNumList=[5], runList=[1])
main.add_module("ParticleGun", **param_pGun)
si.add_simulation(main)

main.add_module(SVDPlotModule())
main.add_module(CDCPlotModule())

b2.process(main)
