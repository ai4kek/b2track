#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################
import basf2
import basf2 as basf2
from ROOT import Belle2
import mdst
import tracking as trkx
import json
from src.tracking_metrics import TrackMetrics


class TrackingMetrics(basf2.Module):
    def __init__(self, params=None, final_state=None):
        super().__init__()
        self.params = params or {}
        self.final_state = final_state or "unknown"

    def initialize(self):
        self.MCParticles = Belle2.PyStoreArray("MCParticles")
        self.Tracks = Belle2.PyStoreArray("Tracks")
        self.matched_mc_particles = 0
        self.selected_mc_particles = 0
        self.total_mc_particles = 0
        self.matched_reco_tracks = 0
        self.selected_reco_tracks = 0
        return 0

    def event(self):
        self.total_mc_particles += self.MCParticles.getEntries()
        self.selected_reco_tracks += self.Tracks.getEntries()
        for track in self.Tracks:
            if track.getRelated("MCParticles"):
                self.matched_reco_tracks += 1
        for mc in self.MCParticles:
            if (
                abs(mc.getPDG()) == 211
                and mc.hasStatus(1)
                and mc.hasSeenInDetector(Belle2.Const.DetectorSet(Belle2.Const.CDC))
            ):
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

        # Save metrics and parameters
        row = {
            **self.params,
            "efficiency": efficiency,
            "purity": purity,
            "final_state": self.final_state,
        }
        csv_file = "track_metrics.csv"
        file_exists = os.path.exists(csv_file)

        with open(csv_file, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
        return 0


# Reproducibility
basf2.set_random_seed(12345)

# Steering Path
main = basf2.Path()

final_state = "mixed"
main.add_module("RootInput", inputFileName=f"dataset/{final_state}_sim.root")

# Tracking reconstruction
trkx.add_tracking_reconstruction(
    path=main,
    components=None,
    pruneTracks=False,
    mcTrackFinding=False,
    skipGeometryAdding=False,
)

# Load ToCDCCKF parameter set
with open("current_params.json", "r") as f:
    params = json.load(f)

# Inject parameters into ToCDCCKF
basf2.set_module_parameters(main, name="ToCDCCKF", recursive=True, **params)

# Calculate tracking metrics
main.add_module(TrackingMetrics(params=params, final_state=final_state))

# Add mDST output (not required for search)
# mdst.add_mdst_output(main, mc=True, filename=f"{final_state}_rec.root")

basf2.process(main)
print(basf2.statistics)
