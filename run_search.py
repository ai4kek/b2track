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
import time
import csv
import os

# Define your parameter search space

params = {
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

    # Run basf2 script and measure execution time
    start_time = time.time()
    subprocess.run(["basf2", "run_tracking.py"])
    execution_time = time.time() - start_time
    print(f"Trial execution time: {execution_time:.2f} seconds")

    # Update metrics.csv with execution time
    metrics_file = "metrics.csv"
    if os.path.exists(metrics_file):
        # Read the last line to update it with execution time
        with open(metrics_file, "r") as f:
            lines = f.readlines()
            if len(lines) > 1:  # Has header and at least one data row
                header = lines[0].strip().split(",")
                last_row = lines[-1].strip().split(",")

                # Create dict from last row
                row_dict = dict(zip(header, last_row))
                row_dict["execution_time"] = f"{execution_time:.2f}"

                # Write back all lines except last
                with open(metrics_file, "w") as f:
                    f.writelines(lines[:-1])
                    # Write updated last row
                    writer = csv.DictWriter(f, fieldnames=row_dict.keys())
                    writer.writerow(row_dict)
