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
from ROOT import Belle2
import matplotlib.cm as colormap
from matplotlib.patches import Circle
import matplotlib.pyplot as plt
from basf2 import Module, Path, process, B2INFO, B2WARNING
from simulation import add_simulation


def plot(x, y, col, show=0):
    """
    Plot a list of x/y values.

    Returns a pyplot.figure that can be saved.
    """
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111)

    # draw the x/y arrays. note that looping over the hits and
    # drawing them individually would be much slower
    for i in range(len(col)):
        ax.plot(x[i], y[i], marker='.', color=col[i], linestyle='None', markersize=5)

    ax.set_title('SVDSimHits')
    ax.set_xlabel('x [cm]')
    ax.set_ylabel('y [cm]')
    ax.axis('scaled')

    ax.set_xlim(-15, 15)
    ax.set_ylim(-15, 15)
    fig.tight_layout()
    if show:
        plt.show()
    return fig


class SVDPlotModule(Module):
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
        simhits = Belle2.PyStoreArray('SVDSimHits')
        geoCache = Belle2.VXD.GeoCache.getInstance()

        # list of lists of simhit positions, one list per mcpart
        trackhits_x = []
        trackhits_y = []

        mcparts = []
        for hit in simhits:
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
            info = geoCache.getSensorInfo(hit.getSensorID())
            hitpos = info.pointToGlobal(hit.getPosIn())
            trackhits_x[idx].append(hitpos.X())
            trackhits_y[idx].append(hitpos.Y())

        npart = len(mcparts)
        if npart > 0:
            # plot the (x,y) list on a matplotlib figure
            col = [colormap.jet(1.0 * c / (npart - 1)) for c in range(npart)]
            fig = plot(trackhits_x, trackhits_y, col)

            filename = f'svdhits_{self.num_events}.png'
            if os.path.lexists(filename):
                B2WARNING(filename + ' exists, overwriting ...')
            else:
                B2INFO('creating ' + filename + ' ...')
            fig.savefig(filename)

        self.num_events += 1

    def terminate(self):
        """reimplementation of Module::terminate()."""
        B2INFO('terminating SVDPlotModule')


# Normal steering file part begins here

# choose the particles you want to simulate
param_pGun = {
    'pdgCodes': [211, -211],
    'nTracks': 4,
    'varyNTracks': 0,
    'momentumGeneration': 'uniform',
    'momentumParams': [0.4, 1.6],
    'thetaGeneration': 'uniform',
    'thetaParams': [60., 120.],
    'phiGeneration': 'uniform',
    'phiParams': [0, 360],
    'vertexGeneration': 'uniform',
    'xVertexParams': [0.0, 0.0],
    'yVertexParams': [0.0, 0.0],
    'zVertexParams': [0.0, 0.0],
}

# Create main path
main = Path()
main.add_module('EventInfoSetter', evtNumList=[5])
main.add_module('ParticleGun', **param_pGun)
add_simulation(main)
main.add_module(SVDPlotModule())

process(main)
