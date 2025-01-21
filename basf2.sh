#!/bin/bash

# setup a basf2 release on KEKCC/NAF
# source /cvmfs/belle.cern.ch/tools/b2setup release-08-02-04

# setup a basf2 release on PC
# source /export/home/adeel/belle2/tools/b2setup release-08-02-04

# setup a basf2 development on PC
# source /export/home/adeel/belle2/tools/b2setup
# source /export/home/adeel/belle2/develop/b2setup

# Define default steering file
steering_file="mc_signal.py"

# Override steering file if an argument is provided
if [[ -n "$1" ]]; then
  steering_file="$1"
fi

# Extract script name without the .py extension
script_name=$(basename "$steering_file" .py)

# Check if the steering file exists before execution
if [[ ! -f "$steering_file" ]]; then
  echo "Error: Steering file '$steering_file' does not exist."
  exit 1
fi

# Function to Show a Spinner
show_spinner() {
  local pid=$1
  local delay=0.1
  local spin_chars='|/-\'
  while kill -0 $pid 2>/dev/null; do
    for char in $spin_chars; do
      printf "\rRunning... %s " "$char"
      sleep $delay
    done
  done
  printf "\rRunning... Done!\n"
}

# Execute steering file and log the output in background
basf2 "$steering_file" > "${script_name}.log" 2>&1 &

# Get the PID of the basf2 process
basf2_pid=$!

# Show spinner while the basf2 process is running
show_spinner $basf2_pid

# Wait for basf2 to complete
wait $basf2_pid
exit_code=$?


# Check if the script executed successfully
if [[ $? -eq 0 ]]; then
  echo "Python script executed successfully. Log saved to '${script_name}.log'."
else
  echo "Error: Python script execution failed. Check '${script_name}.log' for details."
  exit 1
fi
