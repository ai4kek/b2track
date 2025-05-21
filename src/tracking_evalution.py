#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

# Based on the TrackEvaluation module from the GNN hit cleanup by G. Heine.

import csv
import os

import basf2 as b2
import numpy as np
from ROOT import Belle2
from scipy.stats import norm


def calc_confidence_interval(k, n, confidence=0.95):
    """
    Calculate the Wilson score confidence interval for a proportion.

    Parameters:
        k (int or array-like): Number of successes.
        n (int or array-like): Number of trials.
        confidence (float): Confidence level (e.g., 0.95 for 95%).

    Returns:
        tuple: (mean, error) where error is [lower_error, upper_error]
    """
    k = np.asarray(k)
    n = np.asarray(n)

    if np.any(n == 0):
        return np.nan, [np.nan, np.nan]

    z = norm.ppf(1 - (1 - confidence) / 2)
    phat = k / n

    denom = 1 + z**2 / n
    center = (phat + z**2 / (2 * n)) / denom
    margin = (z * np.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2))) / denom

    lower = center - margin
    upper = center + margin

    error = [center - lower, upper - center]
    return center, error


class TrackEvaluation(b2.Module):
    """
    Module to evaluate tracking performance metrics including hit efficiency and hit purity.
    """

    def __init__(self, params=None, finalstate=None, filename=None):
        """
        Initialize the TrackEvaluation module.
        """
        super().__init__()
        self.minNHits = 7
        self.params = params or {}
        self.finalstate = finalstate or "unknown"
        self.filename = filename or "metrics.csv"

    def initialize(self):
        """Initialize data structures for storing hit information."""
        self.tracks = Belle2.PyStoreArray("Tracks")
        self.hit_eff, self.hit_eff_err = [], []
        self.hit_pur, self.hit_pur_err = [], []

    def event(self):
        """Process each event to calculate hit efficiency and purity for tracks."""
        for track in self.tracks:
            # Calculate hit efficiency and purity with their Wilson score intervals
            hit_eff, hit_eff_err = self.calculate_hit_efficiency(track)
            hit_pur, hit_pur_err = self.calculate_hit_purity(track)

            # Store results if calculations were successful
            if hit_eff is not None and hit_pur is not None:
                self.hit_eff.append(hit_eff)
                self.hit_eff_err.append(hit_eff_err)
                self.hit_pur.append(hit_pur)
                self.hit_pur_err.append(hit_pur_err)

    def terminate(self):
        """Calculate and print final metrics at the end of processing."""
        super().terminate()

        # Calculate mean and error for hit efficiency
        hit_eff_mean = np.nanmean(np.array(self.hit_eff)) if self.hit_eff else np.nan
        hit_eff_err = (
            np.linalg.norm(np.array(self.hit_eff_err), axis=0) / len(self.hit_eff)
            if self.hit_eff
            else [np.nan, np.nan]
        )

        # Calculate mean and error for hit purity
        hit_pur_mean = np.nanmean(np.array(self.hit_pur)) if self.hit_pur else np.nan
        hit_pur_err = (
            np.linalg.norm(np.array(self.hit_pur_err), axis=0) / len(self.hit_pur)
            if self.hit_pur
            else [np.nan, np.nan]
        )

        # Calculate F1 score (converted to percentage for consistency)
        f1_score, f1_err = self.calculate_f1_score(hit_eff_mean, hit_pur_mean)
        f1_percent = f1_score * 100  # Convert to percentage
        f1_err_percent = [e * 100 for e in f1_err]  # Convert errors to percentage

        # Calculate F1 score using Wilson score interval corners
        f1_score_wilson, f1_err_wilson = self.calculate_f1_score_wilson(
            hit_eff_mean, hit_pur_mean, hit_eff_err, hit_pur_err
        )
        f1_percent_wilson = f1_score_wilson * 100  # Convert to percentage
        f1_err_percent_wilson = [
            e * 100 for e in f1_err_wilson
        ]  # Convert errors to percentage

        # Print metrics (all in percentage format)
        print(
            f"Hit Efficiency  : {hit_eff_mean:.2%} +{hit_eff_err[1]:.2%} -{hit_eff_err[0]:.2%}"
        )
        print(
            f"Hit Purity      : {hit_pur_mean:.2%} +{hit_pur_err[1]:.2%} -{hit_pur_err[0]:.2%}"
        )
        print(
            f"F1 Score        : {f1_percent:.2f}% +{f1_err_percent[1]:.2f}% -{f1_err_percent[0]:.2f}%"
        )
        print(
            f"F1 Score Wilson : {f1_percent_wilson:.2f}% +{f1_err_percent_wilson[1]:.2f}% -{f1_err_percent_wilson[0]:.2f}%"
        )

        # Header order
        field_order = [
            *list(self.params.keys()),  # Parameters first
            "efficiency",
            "purity",
            "f1",
            "finalstate",  # Then metrics
            "execution_time",
            "worker_id",
            "trial_number",  # Then execution info
        ]

        # Add metrics
        row = {
            **self.params,  # Parameters from JSON
            "efficiency": f"{hit_eff_mean:.4f}",  # Efficiency
            "purity": f"{hit_pur_mean:.4f}",  # Purity
            "f1": f"{f1_score:.4f}",  # F1 score
            "finalstate": self.finalstate,  # Final state
            "execution_time": "",  # Left empty for optimization scripts
            "worker_id": "",  # Left empty for optimization scripts
            "trial_number": "",  # Left empty for optimization scripts
        }

        file_exists = os.path.exists(self.filename)
        with open(self.filename, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=field_order)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

        return 0

    def calculate_hit_efficiency(self, track):
        """
        Calculate hit efficiency for a single track.

        Args:
            track: Track object from which to calculate hit efficiency

        Returns:
            tuple: (hit_efficiency, hit_efficiency_error) or (None, None) if calculation not possible
        """
        MChits_pertrack = 0
        track_related_MChits = 0

        try:
            related_recotrack = track.getRelationsWith("RecoTracks")[0]
            track_related_hits = related_recotrack.getRelationsWith("CDCHits").size()
            if track_related_hits < self.minNHits:
                return None, None

            related_mcparticles = track.getRelationsWith("MCParticles")
            if related_mcparticles.size() == 0:
                return None, None

            # Count total MC hits and matched hits
            for mcparticle in related_mcparticles:
                hitrelations = mcparticle.getRelationsWith("CDCHits")
                MChits_pertrack += hitrelations.size()
                for hit in hitrelations:
                    if related_recotrack in hit.getRelationsWith("RecoTracks"):
                        track_related_MChits += 1

            # Calculate efficiency with confidence interval
            if MChits_pertrack > 0:
                return calc_confidence_interval(track_related_MChits, MChits_pertrack)

        except (IndexError, AttributeError) as e:
            b2.B2WARNING(f"Error calculating hit efficiency: {str(e)}")

        return None, None

    def calculate_hit_purity(self, track):
        """
        Calculate hit purity for a single track.

        Args:
            track: Track object from which to calculate hit purity

        Returns:
            tuple: (hit_purity, hit_purity_error) or (None, None) if calculation not possible
        """
        track_related_MChits = 0

        try:
            related_recotrack = track.getRelationsWith("RecoTracks")[0]
            track_related_hits = related_recotrack.getRelationsWith("CDCHits").size()
            if track_related_hits < self.minNHits:
                return None, None

            related_mcparticles = track.getRelationsWith("MCParticles")
            if related_mcparticles.size() == 0:
                return None, None

            # Count matched hits
            for mcparticle in related_mcparticles:
                hitrelations = mcparticle.getRelationsWith("CDCHits")
                for hit in hitrelations:
                    if related_recotrack in hit.getRelationsWith("RecoTracks"):
                        track_related_MChits += 1

            # Calculate purity with confidence interval
            if track_related_hits > 0:
                return calc_confidence_interval(
                    track_related_MChits, track_related_hits
                )

        except (IndexError, AttributeError) as e:
            b2.B2WARNING(f"Error calculating hit purity: {str(e)}")

        return None, None

    def calculate_f1_score(self, efficiency, purity, eff_err=None, pur_err=None):
        """
        Calculate the F1 score from efficiency and purity with error propagation.

        Uses partial derivatives for error propagation.

        Args:
            efficiency: Hit efficiency value (0-1)
            purity: Hit purity value (0-1)
            eff_err: Efficiency error as [lower, upper]
            pur_err: Purity error as [lower, upper]

        Returns:
            tuple: (f1_score, [lower_error, upper_error])
        """
        if np.isnan(efficiency) or np.isnan(purity) or (efficiency + purity) == 0:
            return np.nan, [np.nan, np.nan]

        # Calculate F1 score
        f1 = 2 * (efficiency * purity) / (efficiency + purity)

        # If no errors provided, return F1 with zero error
        if eff_err is None or pur_err is None:
            return f1, [0, 0]

        # Calculate partial derivatives for error propagation
        denom = (efficiency + purity) ** 2
        df_de = 2 * purity**2 / denom  # Partial derivative w.r.t. efficiency
        df_dp = 2 * efficiency**2 / denom  # Partial derivative w.r.t. purity

        # Calculate error components
        # For upper error: use upper error for positive derivatives, lower for negative
        upper_err = np.sqrt(
            (max(0, df_de) * eff_err[1]) ** 2
            + (max(0, df_dp) * pur_err[1]) ** 2
            + (min(0, df_de) * eff_err[0]) ** 2
            + (min(0, df_dp) * pur_err[0]) ** 2
        )

        # For lower error: use lower error for positive derivatives, upper for negative
        lower_err = np.sqrt(
            (max(0, df_de) * eff_err[0]) ** 2
            + (max(0, df_dp) * pur_err[0]) ** 2
            + (min(0, df_de) * eff_err[1]) ** 2
            + (min(0, df_dp) * pur_err[1]) ** 2
        )

        return f1, [lower_err, upper_err]

    def calculate_f1_score_wilson(self, efficiency, purity, eff_err=None, pur_err=None):
        """
        Calculate the F1 score from efficiency and purity with error propagation
        using Wilson score interval corners.

        This method evaluates the F1 score at the four corners of the error box
        defined by the Wilson score confidence intervals of efficiency and purity.

        Args:
            efficiency: Hit efficiency value (0-1)
            purity: Hit purity value (0-1)
            eff_err: Efficiency error as [lower, upper] from Wilson score interval
            pur_err: Purity error as [lower, upper] from Wilson score interval

        Returns:
            tuple: (f1_score, [lower_error, upper_error])
        """
        if np.isnan(efficiency) or np.isnan(purity) or (efficiency + purity) == 0:
            return np.nan, [np.nan, np.nan]

        # Calculate F1 score
        f1 = 2 * (efficiency * purity) / (efficiency + purity)

        # If no errors provided, return F1 with zero error
        if eff_err is None or pur_err is None:
            return f1, [0, 0]

        # Calculate the F1 score at the four corners of the error box
        # to properly account for the asymmetric errors
        f1_vals = [
            # Base value
            f1,
            # Efficiency up, purity up
            (
                2
                * ((efficiency + eff_err[1]) * (purity + pur_err[1]))
                / (efficiency + eff_err[1] + purity + pur_err[1])
                if (efficiency + eff_err[1] + purity + pur_err[1]) > 0
                else 0
            ),
            # Efficiency up, purity down
            (
                2
                * ((efficiency + eff_err[1]) * max(0, purity - pur_err[0]))
                / (efficiency + eff_err[1] + max(0, purity - pur_err[0]))
                if (efficiency + eff_err[1] + max(0, purity - pur_err[0])) > 0
                else 0
            ),
            # Efficiency down, purity up
            (
                2
                * (max(0, efficiency - eff_err[0]) * (purity + pur_err[1]))
                / (max(0, efficiency - eff_err[0]) + purity + pur_err[1])
                if (max(0, efficiency - eff_err[0]) + purity + pur_err[1]) > 0
                else 0
            ),
            # Efficiency down, purity down
            (
                2
                * (max(0, efficiency - eff_err[0]) * max(0, purity - pur_err[0]))
                / (max(0, efficiency - eff_err[0]) + max(0, purity - pur_err[0]))
                if (max(0, efficiency - eff_err[0]) + max(0, purity - pur_err[0])) > 0
                else 0
            ),
        ]

        # Filter out any invalid F1 values (shouldn't happen with proper inputs)
        valid_f1_vals = [x for x in f1_vals if not np.isnan(x) and x >= 0 and x <= 1]

        if not valid_f1_vals:  # If no valid F1 values, return NaN
            return np.nan, [np.nan, np.nan]

        # Calculate the maximum and minimum F1 values
        f1_min = min(valid_f1_vals)
        f1_max = max(valid_f1_vals)

        # Calculate asymmetric errors
        lower_err = f1 - f1_min
        upper_err = f1_max - f1

        return f1, [lower_err, upper_err]
