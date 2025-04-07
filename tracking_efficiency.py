#!/usr/bin/env python3

import basf2
import mdst
import logging
from ROOT import Belle2


class TrackingMetrics(basf2.Module):
    """Calculate Tracking Efficiency and Purity from the mDST."""

    def initialize(self):
        self.matched_mc_particles = 0
        self.total_mc_particles = 0
        self.matched_reco_tracks = 0
        self.total_reco_tracks = 0
        return 0

    def event(self):

        # Get StoreArray of MCParticles
        mc_particles = Belle2.PyStoreArray("MCParticles")
        self.total_mc_particles += mc_particles.getEntries()

        # Get StoreArray of Tracks or TrackFitResults
        reco_tracks = Belle2.PyStoreArray("Tracks")
        self.total_reco_tracks += reco_tracks.getEntries()

        # Count matched Tracks
        for track in reco_tracks:
            # track_to_particle = track.getRelatedTo("MCParticles")
            track_to_particle = track.getRelated("MCParticles")

            # it relation exists (not nullptr), there might a better way to check
            if track_to_particle:
                self.matched_reco_tracks += 1

        # Count matched MC Particles
        for particle in mc_particles:
            # particle_to_track = particle.getRelatedFrom("Tracks")
            particle_to_track = particle.getRelated("Tracks")

            # it relation exists (not nullptr), there might a better way to check
            if particle_to_track:
                # print(f"Relation name: {particle_to_track.GetName()}")
                self.matched_mc_particles += 1

        return 0

    def terminate(self):

        # overall purity
        purity = 0
        if self.total_reco_tracks > 0:
            purity = self.matched_reco_tracks / self.total_reco_tracks

        print(f"\nTracking Purity: {purity:.4f}")
        print(f"Matched reconstructed tracks: {self.matched_reco_tracks}")
        print(f"Total reconstructed tracks: {self.total_reco_tracks}")

        # overall efficiency
        efficiency = 0
        if self.total_mc_particles > 0:
            efficiency = self.matched_mc_particles / self.total_mc_particles

        print(f"\nTracking Efficiency: {efficiency:.4f}")
        print(f"Matched MC particles: {self.matched_mc_particles}")
        print(f"Total MC particles: {self.total_mc_particles}")

        return 0


class TrackingMetrics_old(basf2.Module):
    def initialize(self):

        # Tracks StoreArray
        # self.reco_tracks = Belle2.PyStoreArray('Tracks')
        # self.reco_tracks.isRequired()

        # MCParticles StoreArray
        # self.mc_particles = Belle2.PyStoreArray('MCParticles')
        # self.mc_particles.isRequired()

        self.val_counter1 = 0
        self.val_counter2 = 0

        # counters
        self.matched_mc_particles = 0
        self.total_mc_particles = 0

        self.total_reconstructable_mc = 0

        self.matched_reco_tracks = 0
        self.total_reco_tracks = 0
        return 0

    def event(self):

        # Get StoreArray of MCParticles
        mc_particles = Belle2.PyStoreArray("MCParticles")
        self.total_mc_particles += mc_particles.getEntries()
        # self.total_mc_particles += len(mc_particles)

        # Get StoreArray of Tracks or TrackFitResults
        reco_tracks = Belle2.PyStoreArray("Tracks")
        self.total_reco_tracks += reco_tracks.getEntries()
        # self.total_reco_tracks += len(reco_tracks)

        # Get relations (How to access and use?)
        # relations = Belle2.PyStoreArray('TracksToMCParticles')

        # tracking/tests/track_to_mcparticle_relation_test.py
        for track in reco_tracks:
            track_to_particle_relations = track.getRelationsTo("MCParticles")
            n_relations = track_to_particle_relations.size()
            if n_relations == 0:
                pass  # print(f"No. of relations from Tracks to MCParticles: {n_relations}")

        for particle in mc_particles:
            particle_to_track_relation = particle.getRelationsTo("Tracks")
            n_relations = particle_to_track_relation.size()
            if n_relations == 0:
                pass  # print(f"No. of relations from MCParticles to Tracks: {n_relations}")

        # TODO: Purity: Number of matched reconstructed tracks divided by total
        # reconstructed tracks. We already have 'total_reco_tracks', but need to
        # find 'matched_reco_tracks' by counting reconstructed tracks that are
        # matched to an mc particle per event, then aggregate for all events.

        # Count matched Tracks
        for track in reco_tracks:
            track_to_particle = track.getRelated("MCParticles")  # getRelatedTo()

            # it relation exists (not nullptr), there might a better way to check
            if track_to_particle:
                # print(f"Relation name: {track_to_particle.GetName()}")
                self.matched_reco_tracks += 1

        # TODO: Efficiency: Number of matched mc particles divided by total
        # generated particles. We already have 'total_mc_particles', but need to
        # find 'matched_mc_particles' by counting mc particles that are matched
        # to a reconstructed track per event, then aggregate for all events.

        # Count matched MC Particles
        for particle in mc_particles:
            particle_to_track = particle.getRelated("Tracks")  # getRelatedFrom()

            # it relation exists (not nullptr), there might a better way to check
            if particle_to_track:
                # print(f"Relation name: {particle_to_track.GetName()}")
                self.matched_mc_particles += 1

        return 0

    def terminate(self):

        # overall purity
        purity = 0
        if self.total_reco_tracks > 0:
            purity = self.matched_reco_tracks / self.total_reco_tracks

        print(f"\nTracking Purity: {purity:.4f}")
        print(f"Matched reconstructed tracks: {self.matched_reco_tracks}")
        print(f"Total reconstructed tracks: {self.total_reco_tracks}")

        # overall efficiency
        efficiency = 0
        if self.total_mc_particles > 0:
            efficiency = self.matched_mc_particles / self.total_mc_particles

        print(f"\nTracking Efficiency: {efficiency:.4f}")
        print(f"Matched MC particles: {self.matched_mc_particles}")
        print(f"Total MC particles: {self.total_mc_particles}")

        # Save metrics to file
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
