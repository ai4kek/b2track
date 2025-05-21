#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################


import basf2

from src.tracking_evalution import TrackEvaluation
from src.tracking_metrics import TrackMetrics

# Reproducibility
basf2.set_random_seed(12345)

# Steering Path
main = basf2.Path()

finalstate = "mixed"
main.add_module("RootInput", inputFileName=f"dataset/{finalstate}_rec.root")

# Dummy ToCDCCKF params
params = {"trial": 1, "param1": 1.0, "param2": 0.25, "myTag": "experimentA"}

# Tracking Metrics
# metrics = TrackMetrics(params, finalstate, filename="test.csv")
evaluate = TrackEvaluation(params, finalstate, filename="test.csv")
main.add_module(evaluate)
basf2.process(main)
