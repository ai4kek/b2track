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
from src.tracking_metrics import TrackMetrics  # non-verbosed
from src.tracking_metrics import TrackingMetrics  # verbosed

# Reproducibility
basf2.set_random_seed(12345)

# Steering Path
main = basf2.Path()

finalstate = "mixed"
main.add_module("RootInput", inputFileName=f"dataset/{finalstate}_mdst_svd.root")

# Dummy ToCDCCKF params
params = {"trial": 1, "param1": 1.0, "param2": 0.25, "myTag": "experimentA"}

# Tracking Metrics
# metrics = TrackingMetrics(params, final_state, filename="test.csv")
metrics = TrackMetrics(params, finalstate, filename="test.csv")
main.add_module(metrics)
basf2.process(main)
