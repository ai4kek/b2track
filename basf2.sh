#!/bin/bash

# setup a basf2 release on KEKCC/NAF
# source /cvmfs/belle.cern.ch/tools/b2setup release-08-02-04

# setup a basf2 release on PC
# source /export/home/adeel/belle2/tools/b2setup release-08-02-04

# setup a basf2 development on PC
source /export/home/adeel/belle2/tools/b2setup
source /export/home/adeel/belle2/develop/b2setup

# steering file
steering_file="mc_signal.py"

if [[ -n "$1" ]]; then
  steering_file="$1"
fi

# execute steering file
basf2 "$steering_file" 2>&1 | tee output.log

# Check if the script executed successfully
if [[ $? -eq 0 ]]; then
  echo "Python script executed successfully."
else
  echo "Error: Python script execution failed."
fi
