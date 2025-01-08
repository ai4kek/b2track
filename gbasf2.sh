#!/bin/bash

# setup basf2 on KEKCC/NAF
# source /cvmfs/belle.cern.ch/tools/b2setup release-08-02-04


for dtype in BB uubar ddbar ssbar ccbar taupair
do 
    gbasf2 ~sayan/btosgamma/reconstruct/BtoKst2Gam.py -p ntuple_MC_${dtype}_1029 -i /belle/collection/MC/RSC_MC15rd_4S_${dtype}_skim_12160100_v1 -s light-2406-ragdoll --cputime 15 --force
done
gbasf2 ~sayan/btosgamma/reconstruct/BtoKst2Gam.py -p ntuple_data_1029 -i /belle/collection/Data/RSC_proc13prompt_4S_skim_12160100_v1 -s light-2406-ragdoll --cputime 15 --force --basf2opt=" -- --isNotMC"
