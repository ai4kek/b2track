#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

import subprocess
import random
import json

# Define your parameter search space

params_1 = {
    # "filter": "size",
    # "pathFilter": "arc_length",
    # "filterParameters": {},
    # "pathFilterParameters": {},
    # "stateBasicFilterParameters": {'maximalHitDistance': 0.15},
    # "stateExtrapolationFilterParameters": {},
    # "stateFinalFilterParameters": {},
    # "statePreFilterParameters": {},
    "exportAllTracks": False,  #
    "exportTracks": True,  #
    "ignoreTracksWithCDChits": True,  #
    "setTakenFlag": True,  #
}

search_space = {
    "maximalDeltaPhi": [0.2, 0.3, 0.4, 0.5],
    "maximalLayerJump": [3, 4, 5],
    "minimalPtRequirement": [0.0, 0.1],
    "pathMaximalCandidatesInFlight": [2, 3, 4],
    "stateMaximalHitCandidates": [3, 4, 5],
}


def get_random_params(space):
    return {k: random.choice(v) for k, v in space.items()}


# Number of trials
num_trials = 10

for trial in range(num_trials):
    print(f"\nTrial {trial + 1}/{num_trials}")
    params = get_random_params(search_space)

    # Save to JSON
    with open("current_params.json", "w") as f:
        json.dump(params, f, indent=2)

    # Run basf2 script
    subprocess.run(["basf2", "run_tracking.py"])
