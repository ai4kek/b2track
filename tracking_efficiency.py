#!/usr/bin/env python3

import basf2
import mdst
import logging
from ROOT import Belle2


class TrackingMetrics(basf2.Module):
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
            # track_to_particle_relations = track.getRelationsTo("MCParticles")
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

            # Primary, charged pions seen in CDC
            isGoodParticle = isPrimary and isChargedPion and isSeen

            if isGoodParticle:

                # count selected particles
                self.selected_mc_particles += 1

                # matched to a track with no clones
                # FIXME: How to handle clones?

                # particle_to_track_relation = mc.getRelationsFrom("Tracks")
                particle_to_track_relation = mc.getRelatedFrom("Tracks")
                # particle_to_track_relation = mc.getRelated("Tracks")

                # num_relations = len(particle_to_track_relation)
                num_relations = particle_to_track_relation
                if num_relations:
                    self.matched_mc_particles += 1

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

        # save metrics to file
        with open("track_metrics.csv", "w") as f:
            f.write("metric,value\n")
            f.write(f"efficiency,{efficiency}\n")
            f.write(f"purity,{purity}\n")

        return 0


# Steering Path
basf2.set_random_seed(12345)
logging.basicConfig(level=logging.INFO)

main = basf2.Path()

# Reconstructed BBBar events
main.add_module("RootInput", inputFileName="mixed_reco.root")

# Efficiency and Purity Module
metrics = TrackingMetrics()
main.add_module(metrics)
basf2.process(main)
