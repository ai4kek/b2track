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

final_state = "mixed"
main.add_module("RootInput", inputFileName=f"dataset/{final_state}_mdst.root")

# TrackingMetrics Module
params = {"trial": 1, "param1": 1.0, "param2": 0.25, "myTag": "experimentA"}

main.add_module(
    TrackMetrics(params=params, finalstate=final_state, filename="test.csv")
)
basf2.process(main)
