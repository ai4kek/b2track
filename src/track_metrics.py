#!/usr/bin/env python3

import basf2 as b2
from ROOT import Belle2


class TrackMetricsModule(b2.Module):
    """A basf2 module to calculate hit efficiency and purity metrics."""

    def initialize(self):
        """Initialize the module."""
        self.n_total_hits = 0
        self.n_correct_hits = 0
        self.n_found_hits = 0
        return True

    def event(self):
        """Process each event."""
        # Get the DataStore
        dataStore = Belle2.PyStoreObj()

        # Get MCParticles and ReconstructedTracks
        mcParticles = dataStore.get("MCParticles")
        tracks = dataStore.get("ReconstructedTracks")

        if not mcParticles or not tracks:
            return True

        # Process each track
        for track in tracks:
            hits = track.getHits()
            if not hits:
                continue

            self.n_found_hits += len(hits)

            # Count correct hits (hits associated with true MC particle)
            for hit in hits:
                if hit.getMCParticle():
                    self.n_correct_hits += 1

        # Count total true hits from MC particles
        for mcParticle in mcParticles:
            if mcParticle.getPDG() in [11, 13, 211, 321, 2212]:  # e, mu, pi, K, p
                self.n_total_hits += len(mcParticle.getHits())

        return True

    def terminate(self):
        """Calculate and print final metrics."""
        efficiency = (
            self.n_correct_hits / self.n_total_hits if self.n_total_hits > 0 else 0
        )
        purity = self.n_correct_hits / self.n_found_hits if self.n_found_hits > 0 else 0

        print("\n=== Track Metrics ===")
        print(f"Hit Efficiency: {efficiency:.4f}")
        print(f"Hit Purity: {purity:.4f}")
        print(f"Total MC hits: {self.n_total_hits}")
        print(f"Found hits: {self.n_found_hits}")
        print(f"Correct hits: {self.n_correct_hits}")

        # Save metrics to file
        with open("track_metrics.csv", "w") as f:
            f.write("metric,value\n")
            f.write(f"efficiency,{efficiency}\n")
            f.write(f"purity,{purity}\n")

        return True
