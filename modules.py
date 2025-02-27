#!/usr/bin/env python3

# More advanced examples
# - framework/examples/cdcplotmodule.py - A full example that uses matplotlib to plot CDCSimHits
# - framework/examples/interactive_python.py drops into an interactive (i)python shell inside the event() function, allowing exploration of available objects and data structures
# - reconstruction/examples/plot_LL_diff.py - Gets PID log-likelihoods, uses relations to get corresponding MC truth and fills ROOT histograms accordingly


import basf2 as b2
from ROOT import Belle2


class MinModule(b2.Module):
    """A minimal example of a basf2 module in python."""

    def __init__(self):
        """Constructor"""
        # call constructor of base class, required if you implement __init__
        # yourself!
        super().__init__()
        # and do whatever else is necessary like declaring member variables

    def initialize(self):
        """Called once in the beginning just before starting processing"""
        b2.B2INFO("initialize()")

    def beginRun(self):
        """Called every time a run changes before the actual events in that run
        are processed
        """
        b2.B2INFO("beginRun()")

    def event(self):
        """Called once for each event"""
        b2.B2INFO("event()")

    def endRun(self):
        """Called every time a run changes after the actual events in that run
        were processed
        """
        b2.B2INFO("endRun()")

    def terminate(self):
        """Called once after all the processing is complete"""
        b2.B2INFO("terminate()")


class AccessingDataStoreModule(b2.Module):
    """An example of a basf2 module in python which accesses things in the datastore."""

    def initialize(self):
        """Create a member to access event info and the MCParticles
        StoreArray
        """
        #: an example object from the datastore (the metadata collection for the event)
        self.eventinfo = Belle2.PyStoreObj("EventMetaData")

        #: an example array from the datastore (the list of MC particles)
        self.particles = Belle2.PyStoreArray("MCParticles")

    def event(self):
        """Print the number of charged particles and the total charge"""
        n_charged = 0
        total_charge = 0
        for particle in self.particles:
            charge = particle.getCharge()
            if charge:
                n_charged += 1
            total_charge += charge

        b2.B2INFO(
            f"Number of charged particles = {n_charged}, "
            f"total charge of event = {total_charge}"
        )


# create a path
main = b2.Path()

# generate events
main.add_module("EventInfoSetter", evtNumList=[10])

# generate events with 3 tracks (not all of them are charged tracks)
main.add_module("ParticleGun", nTracks=3)

# and add our module
main.add_module(AccessingDataStoreModule())

# run the path
b2.process(main)
