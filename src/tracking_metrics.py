#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

import basf2
import mdst
import logging
from ROOT import Belle2
import os
import csv


# Main Module
class TrackMetrics(basf2.Module):
    def __init__(self, params=None, finalstate=None, filename=None):
        super().__init__()
        self.params = params or {}
        self.finalstate = finalstate or "unknown"
        self.filename = filename or "tracking_metrics.csv"

    def initialize(self):
        self.MCParticles = Belle2.PyStoreArray("MCParticles")
        self.Tracks = Belle2.PyStoreArray("Tracks")

        self.RecoTracks = Belle2.PyStoreArray("RecoTracks")
        self.RecoTracksToMCParticles = Belle2.PyStoreArray("RecoTracksToMCParticles")
        self.CDCHits = Belle2.PyStoreArray("CDCHits")
        self.SVDClusters = Belle2.PyStoreArray("SVDClusters")

        # track finding efficiency and purity
        self.matched_mc_particles = 0
        self.selected_mc_particles = 0
        self.matched_reco_tracks = 0
        self.selected_reco_tracks = 0

        # hit efficiency and purity
        self.total_recotracks_tracks = 0

        return 0

    def event(self):

        self.selected_reco_tracks += self.Tracks.getEntries()
        self.total_recotracks_tracks += self.RecoTracks.getEntries()

        # loop over Tracks
        for track in self.Tracks:
            if track.getRelated("MCParticles"):
                self.matched_reco_tracks += 1

        # loop over Particles
        for mc in self.MCParticles:
            isSelected = (
                abs(mc.getPDG()) == 211
                and mc.hasStatus(1)
                and mc.hasSeenInDetector(Belle2.Const.DetectorSet(Belle2.Const.CDC))
            )

            if isSelected:
                self.selected_mc_particles += 1
                if mc.getRelated("Tracks"):
                    self.matched_mc_particles += 1
        return 0

    def terminate(self):
        efficiency = (
            self.matched_mc_particles / self.selected_mc_particles
            if self.selected_mc_particles > 0
            else 0
        )
        purity = (
            self.matched_reco_tracks / self.selected_reco_tracks
            if self.selected_reco_tracks > 0
            else 0
        )

        print(f"\nTracking Efficiency: {efficiency:.4f}")
        print(f"Tracking Purity: {purity:.4f}")

        print(f"\nTracking Purity: {self.total_recotracks_tracks:.4f}")

        # Save metrics and parameters
        row = {
            **self.params,
            "efficiency": efficiency,
            "purity": purity,
            "finalstate": self.finalstate,
        }

        file_exists = os.path.exists(self.filename)
        with open(self.filename, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())

            if not file_exists:
                writer.writeheader()

            writer.writerow(row)
        return 0


# Main Module (Verbose)
class TrackingMetrics(basf2.Module):
    def __init__(self, params=None, finalstate=None, filename=None):
        super().__init__()
        self.params = params or {}
        self.finalstate = finalstate or "unknown"
        self.filename = filename or "tracking_metrics.csv"

    def initialize(self):
        """initialize"""

        # ------ Tracking Efficiency and Purity ------

        # related StoreArrays
        self.MCParticles = Belle2.PyStoreArray("MCParticles")
        self.Tracks = Belle2.PyStoreArray("Tracks")

        # related counters
        self.matched_mc_particles = 0
        self.selected_mc_particles = 0
        self.total_mc_particles = 0
        self.matched_reco_tracks = 0
        self.selected_reco_tracks = 0

        # ------ Hit Efficiency and Purity ------

        # related StoreArrays
        # self.RecoTrack = Belle2.PyStoreArray('RecoTracks')
        # self.cdchits = Belle2.PyStoreArray('CDCHits')
        # self.svdclusters = Belle2.PyStoreArray('SVDClusters')

        # related counters
        # self.n_simCDCHits = 0, self.matched_simCDCHits = 0
        # self.n_recCDCHits = 0, self.matched_simCDCHits = 0
        # self.n_simSVDHits = 0, self.matched_simCDCHits = 0
        # self.n_recSVDHits = 0, self.matched_simCDCHits = 0

        return 0

    def event(self):
        """event loop"""

        # count total
        self.total_mc_particles += self.MCParticles.getEntries()
        self.selected_reco_tracks += self.Tracks.getEntries()

        # Tracking Purity: Number of matched reconstructed tracks divided by total
        # reconstructed tracks. We already have 'selected_reco_tracks', but need to
        # find 'matched_reco_tracks' by counting reconstructed tracks that are
        # matched to an mc particle per event, then aggregate for all events.

        # Count matched Tracks
        for track in self.Tracks:
            # track_to_particle_relation = track.getRelationsTo("MCParticles")
            # track_to_particle_relation = track.getRelatedTo("MCParticles")
            track_to_particle = track.getRelated("MCParticles")

            # it relation exists (not nullptr), there might a better way to check
            if track_to_particle:
                # print(f"Relation name: {track_to_particle.GetName()}")
                self.matched_reco_tracks += 1

        # Tracking Efficiency: Number of matched mc particles divided by total
        # generated particles. We already have 'total_mc_particles', but need to
        # find 'matched_mc_particles' by counting mc particles that are matched
        # to a reconstructed track per event, then aggregate for all events.

        # Count matched MC Particles
        for mc in self.MCParticles:

            # particle selection criteria
            isChargedPion = abs(mc.getPDG()) == 211  # only charged pions
            isCharged = mc.getCharge() != 0  # only charged particles
            isPrimary = mc.hasStatus(1)  # only primary particles
            isStable = mc.hasStatus(2)  # only stable particles
            isSeen = mc.hasSeenInDetector(  # only seen in CDC
                Belle2.Const.DetectorSet(Belle2.Const.CDC)
            )
            notSecPhyProc = mc.getSecondaryPhysicsProcess() == 0  # only primary process

            # Primary, charged pions seen in CDC
            isSelected = isPrimary and isChargedPion and isSeen and notSecPhyProc

            if isSelected:

                # count selected particles
                self.selected_mc_particles += 1

                # count selected and matched particles
                # particle_to_track_relation = mc.getRelationsFrom("Tracks")
                # particle_to_track_relation = mc.getRelatedFrom("Tracks")
                particle_to_track_relation = mc.getRelated("Tracks")

                # it relation exists (not nullptr), there might a better way to check
                if particle_to_track_relation:
                    # Since its a Track object, we can see more info:

                    # print(f"Track Quality Indicator: {particle_to_track_relation.getQualityIndicator()}")
                    # print(f"Fitted Hypothesis: {particle_to_track_relation.getNumberOfFittedHypotheses()}")

                    self.matched_mc_particles += 1

        # TODO: Find Hit Efficiency & Purity: RecoTracks, CDCHits & SVDClusters

        return 0

    def terminate(self):
        """terminate"""

        # tracking efficiency
        efficiency = 0
        if self.total_mc_particles > 0:
            efficiency = self.matched_mc_particles / self.selected_mc_particles

        print(f"\nTracking Efficiency: {efficiency:.4f}")
        print(f"Matched MC particles: {self.matched_mc_particles}")
        print(f"Selected MC particles: {self.selected_mc_particles}")
        print(f"Total MC particles: {self.total_mc_particles}")

        # tracking purity
        purity = 0
        if self.selected_reco_tracks > 0:
            purity = self.matched_reco_tracks / self.selected_reco_tracks

        print(f"\nTracking Purity: {purity:.4f}")
        print(f"Matched reconstructed tracks: {self.matched_reco_tracks}")
        print(f"Selected reconstructed tracks: {self.selected_reco_tracks}")

        # save results to CSV
        self.save_metrics(efficiency, purity)

        return 0

    def save_metrics(self, efficiency, purity):
        """Save ToCDCCKF parameters along with Tracking Efficiency and Purity"""

        row_data = self.params.copy()
        row_data.update(
            {
                "efficiency": efficiency,
                "purity": purity,
                "finalstate": self.finalstate,
            }
        )

        file_exists = os.path.exists(self.filename)
        with open(self.filename, mode="a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=row_data.keys())

            if not file_exists:
                writer.writeheader()

            writer.writerow(row_data)
