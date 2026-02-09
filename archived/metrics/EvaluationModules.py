# Load packages
import basf2 as b2
import numpy as np
from astropy.stats import binom_conf_interval
from ROOT import Belle2


def calc_confidence_interval(k, n, interval="wilson"):
    """Function to calculate the Wilson score confidence interval for a proportion."""
    k = np.array(k)
    n = np.array(n)

    if n > 0:
        lower, upper = binom_conf_interval(k=k, n=n, interval=interval)
        mean = k / n
        error = [mean - lower, upper - mean]
    else:
        mean = np.nan
        error = [np.nan, np.nan]
    return mean, error


class HitEvaluate(b2.Module):

    def initialize(self):
        """
        Sets up module resources and initializes data structures for storing hit information.
        """
        # Access event metadata, CDC (wire) hit collections and CDC geometry parameters
        self.eventinfo = Belle2.PyStoreObj("EventMetaData")
        self.wire_hits_vector = Belle2.PyStoreObj("CDCWireHitVector")
        self.k_eff, self.n_eff = 0.0, 0.0
        self.k_fake, self.n_fake = 0.0, 0.0
        self.k_bkgr, self.n_bkgr = 0.0, 0.0

    def event(self):
        wire_hit_vector = self.wire_hits_vector.unwrap()

        efficiencies = []
        fake_rates = []
        background_rejections = []

        for m_hit_id in range(wire_hit_vector.size()):
            wire_hit = wire_hit_vector.at(m_hit_id)  # This is a CDCWireHit
            signal_flag = not wire_hit.getAutomatonCell().hasBackgroundFlag()

            # evaluate cleanup
            is_signal = wire_hit.getHit().getRelationsWith("MCParticles").size() > 0

            efficiency = (
                1 if is_signal and signal_flag else (
                    0 if is_signal else np.nan)
            )
            purity = 1 if signal_flag and is_signal else (
                0 if signal_flag else np.nan)
            fake_rate = 1 - purity
            background_rejection = (
                1
                if not is_signal and not signal_flag
                else (0 if not is_signal else np.nan)
            )

            efficiencies.append(efficiency)
            fake_rates.append(fake_rate)
            background_rejections.append(background_rejection)

        # Count successes and trials
        efficiencies = np.array(efficiencies)
        self.k_eff += np.nansum(efficiencies)  # Number of successes
        self.n_eff += np.sum(~np.isnan(efficiencies))  # Number of trials

        fake_rates = np.array(fake_rates)
        self.k_fake += np.nansum(fake_rates)  # Number of successes
        self.n_fake += np.sum(~np.isnan(fake_rates))  # Number of trials

        background_rejections = np.array(background_rejections)
        self.k_bkgr += np.nansum(background_rejections)  # Number of successes
        # Number of trials
        self.n_bkgr += np.sum(~np.isnan(background_rejections))

    def terminate(self):
        super().terminate()
        efficiencies_mean, efficiencies_err = calc_confidence_interval(
            self.k_eff, self.n_eff
        )
        fake_rates_mean, fake_rates_err = calc_confidence_interval(
            self.k_fake, self.n_fake
        )
        rejection_mean, rejection_err = calc_confidence_interval(
            self.k_bkgr, self.n_bkgr
        )

        efficiencies = f"{efficiencies_mean:.2%} + {efficiencies_err[1]:.2%} - {efficiencies_err[0]:.2%}"
        fake_rates = (
            f"{fake_rates_mean:.2%} + {fake_rates_err[1]:.2%} - {fake_rates_err[0]:.2%}"
        )
        background_rejection = (
            f"{rejection_mean:.2%} + {rejection_err[1]:.2%} - {rejection_err[0]:.2%}"
        )

        metrics = [efficiencies, fake_rates, background_rejection]
        np.save("tmp_hit_metrics.npy", metrics)


class TrackEvaluate(b2.Module):

    def __init__(self, minNHits=7):
        super().__init__()
        self.minNHits = minNHits

    def initialize(self):
        """
        Sets up module resources and initializes data structures for storing hit information.
        """
        # Access event metadata, CDC (wire) hit collections and CDC geometry parameters
        self.eventinfo = Belle2.PyStoreObj("EventMetaData")
        self.tracks = Belle2.PyStoreArray("Tracks")
        self.mcparticles = Belle2.PyStoreArray("MCParticles")

        self.hit_eff, self.hit_eff_err = [], []
        self.hit_pur, self.hit_pur_err = [], []
        self.k_cheff, self.n_cheff = 0, 0
        self.k_fiteff, self.n_fiteff = 0, 0
        self.k_findeff, self.n_findeff = 0, 0
        self.k_fake, self.n_fake = 0, 0
        self.k_clone, self.n_clone = 0, 0

    def event(self):

        charge_efficiencies = []
        fitting_efficiencies = []
        finding_efficiencies = []
        fake_rates = []
        clone_rates = []

        # calculate hit efficiency and purity
        for track in self.tracks:
            MChits_pertrack = 0
            track_related_MChits = 0
            related_recotrack = track.getRelationsWith("RecoTracks")[0]
            track_related_hits = related_recotrack.getRelationsWith(
                "CDCHits").size()
            if track_related_hits < self.minNHits:
                continue

            related_mcparticles = track.getRelationsWith("MCParticles")
            if related_mcparticles.size() == 0:
                continue

            for mcparticle in related_mcparticles:
                hitrelations = mcparticle.getRelationsWith("CDCHits")
                MChits_pertrack += hitrelations.size()
                for hit in hitrelations:
                    if related_recotrack in hit.getRelationsWith("RecoTracks"):
                        track_related_MChits += 1

            hit_efficiency, hit_efficiency_error = calc_confidence_interval(
                track_related_MChits, MChits_pertrack
            )
            hit_purity, hit_purity_error = calc_confidence_interval(
                track_related_MChits, track_related_hits
            )

            self.hit_eff.append(hit_efficiency)
            self.hit_eff_err.append(hit_efficiency_error)
            self.hit_pur.append(hit_purity)
            self.hit_pur_err.append(hit_purity_error)

        # calculate track efficiency, fake rate and clone rate
        for mcparticle in self.mcparticles:

            # check whether the MC particle is a primary particle or parents are K0 or Lambda
            m_isprimary = mcparticle.isPrimaryParticle()
            if not m_isprimary == False:
                try:
                    m_particle_mother_mcpdg = mcparticle.getMother().getPDG()
                except ReferenceError:
                    m_particle_mother_mcpdg = -1
            if not m_isprimary and not m_particle_mother_mcpdg in [310, 3122]:
                continue

            # check whether the MC particle has at least self.minNHits (default 7) hits
            hitrelations = mcparticle.getRelationsWith("CDCHits")
            nhitrelations = hitrelations.size()
            if nhitrelations < self.minNHits:
                continue

            # track finding efficiency
            recotrackrelations = mcparticle.getRelationsWith("RecoTracks")
            trackfound = 1 if recotrackrelations.size() > 0 else 0

            # track fitting (charge) efficiency and clone rate
            trackrelations = mcparticle.getRelationsWith("Tracks")
            if trackrelations.size() > 0:
                trackfitted = 1
                for track in trackrelations:
                    trackFitResult = track.getTrackFitResultWithClosestMass(
                        Belle2.Const.muon
                    )
                    chargesign = trackFitResult.getChargeSign()
                    trackfitted_correct_charge = (
                        1 if chargesign == mcparticle.getCharge() else 0
                    )
                clone = trackrelations.size() - 1 if trackrelations.size() > 1 else 0

            else:
                trackfitted = 0
                trackfitted_correct_charge = 0
                clone = np.nan

            # fake rate
            faketrack = 0
            for track in self.tracks:
                mcrelation = track.getRelationsWith("MCParticles")
                faketrack += 1 if mcrelation.size() == 0 else 0

            # store metrics
            charge_efficiencies.append(trackfitted_correct_charge)
            fitting_efficiencies.append(trackfitted)
            finding_efficiencies.append(trackfound)
            fake_rates.append(faketrack)
            clone_rates.append(clone)

        # Count successes and trials
        charge_efficiencies = np.array(charge_efficiencies)
        self.k_cheff += np.nansum(charge_efficiencies)  # Number of successes
        # Number of trials
        self.n_cheff += np.sum(~np.isnan(charge_efficiencies))

        fit_efficiencies = np.array(fitting_efficiencies)
        self.k_fiteff += np.nansum(fit_efficiencies)  # Number of successes
        # Number of trials
        self.n_fiteff += np.sum(~np.isnan(fit_efficiencies))

        finding_efficiencies = np.array(finding_efficiencies)
        # Number of successes
        self.k_findeff += np.nansum(finding_efficiencies)
        # Number of trials
        self.n_findeff += np.sum(~np.isnan(finding_efficiencies))

        fake_rates = np.array(fake_rates)
        self.k_fake += np.nansum(fake_rates)  # Number of successes
        self.n_fake += np.sum(~np.isnan(fake_rates))  # Number of trials

        clone_rates = np.array(clone_rates)
        self.k_clone += np.nansum(clone_rates)  # Number of successes
        self.n_clone += np.sum(~np.isnan(clone_rates))  # Number of trials

    def terminate(self):
        super().terminate()

        hit_eff_mean = np.nanmean(np.array(self.hit_eff))
        hit_eff_err = np.linalg.norm(np.array(self.hit_eff_err), axis=0) / len(
            self.hit_eff
        )
        hit_pur_mean = np.nanmean(np.array(self.hit_pur))
        hit_pur_err = np.linalg.norm(np.array(self.hit_pur_err), axis=0) / len(
            self.hit_eff
        )

        cheff_mean, cheff_err = calc_confidence_interval(
            self.k_cheff, self.n_cheff)
        fiteff_mean, fiteff_err = calc_confidence_interval(
            self.k_fiteff, self.n_fiteff)
        findeff_mean, findeff_err = calc_confidence_interval(
            self.k_findeff, self.n_findeff
        )
        fakes_mean, fakes_err = calc_confidence_interval(
            self.k_fake, self.n_fake)
        clones_mean, clones_err = calc_confidence_interval(
            self.k_clone, self.n_clone)

        hit_efficiencies = (
            f"{hit_eff_mean:.2%} + {hit_eff_err[1]:.2%} - {hit_eff_err[0]:.2%}"
        )
        hit_purities = (
            f"{hit_pur_mean:.2%} + {hit_pur_err[1]:.2%} - {hit_pur_err[0]:.2%}"
        )

        charge_efficiencies = (
            f"{cheff_mean:.2%} + {cheff_err[1]:.2%} - {cheff_err[0]:.2%}"
        )
        fitting_efficiencies = (
            f"{fiteff_mean:.2%} + {fiteff_err[1]:.2%} - {fiteff_err[0]:.2%}"
        )
        finding_efficiencies = (
            f"{findeff_mean:.2%} + {findeff_err[1]:.2%} - {findeff_err[0]:.2%}"
        )
        fake_rates = f"{fakes_mean:.2%} + {fakes_err[1]:.2%} - {fakes_err[0]:.2%}"
        clone_rates = f"{clones_mean:.2%} + {clones_err[1]:.2%} - {clones_err[0]:.2%}"

        metrics = [
            charge_efficiencies,
            fitting_efficiencies,
            finding_efficiencies,
            fake_rates,
            clone_rates,
            hit_efficiencies,
            hit_purities,
        ]
        np.save("tmp_track_metrics.npy", metrics)
