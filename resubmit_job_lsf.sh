#!/bin/bash
# Usage: ./resubmit_worker_lsf.sh <worker_id1> [<worker_id2> ...]
# Example: ./resubmit_worker_lsf.sh 5 7 8

if [ $# -lt 1 ]; then
    echo "Usage: $0 <worker_id1> [<worker_id2> ...]"
    exit 1
fi

WORKER_LIST=()
for id in "$@"; do
    WORKER_ID=$(printf "%03d" "$id")
    rm -v metrics_worker_${WORKER_ID}.csv params_worker_${WORKER_ID}.json logs/logs_worker_${WORKER_ID}.log 2>/dev/null
    WORKER_LIST+=("$id")
done

WORKERS_CSV=$(IFS=, ; echo "${WORKER_LIST[*]}")
echo "Files for workers ${WORKER_LIST[*]} cleaned up."
echo "To resubmit these workers on LSF, run:"
echo "bsub -J \"grid[${WORKERS_CSV}]\" < run_grid_lsf.sh"

# To automatically resubmit, uncomment the following line:
# bsub -J "grid[${WORKERS_CSV}]" < run_grid_lsf.sh
