## _Hyperparameter Optimization (HPO)_

The tracking parameters can be optimized using the Grid Search (_`run_grid.py`_) and the Random Search (_`run_rand.py`_) approachs both locally and on cluster. Since we have no access to _`basf2`_ internals during the optimization, we only rely on tracking efficiency, tracking purity, hit efficiency, and hit purity metrics saved to a CSV file. This is called a **_Black Box Optimization_** approach, where special librraries like **_Optuna_**, **_RayTune_**, **_Ax_**, **_SMAC_**, **_HEBO_**, **_Hyperopt_**, **_Skopt_**, **_Nevergrad_**, , etc can be used, however, we rely on python scientific stack (NumPy, Pandas, SciPy, etc). This choice made the optimization workflow complicated. In anycase, we have worker-specific workflow where each worker runs a trials assigned to it independently. Once all workers are done, we aggregate the results and select the best parameters based on F1 score.



### _Grid Search Workflow_

To run exhaustive grid search, we use the _`run_grid.py`_  script. The flow of the script is as follows:

```shell
# (1) run_grid.py
# main steering script that handles parallelization, chunking, and aggregation
| main()
| │
| ├── Selects execution mode (single or multi-worker, cluster)
| ├── Splits the parameter space and creates chunks of trials
| ├── Distirbutes chunks to workers
| ├── Run process_chunk() # processes trials one by one in the chunk
| │   ├── trial_objective()  # handles one trial at a time
| │   │  └── run_tracking_with_params() # runs basf2 tracking
| │   │     └── run_tracking_svd.py  # SVD-only or Full (run_tracking.py)
| │   └── finish trials in a chunk
| └── (optional) aggregate metrics into a single CSV file
└ └─ Terminate HPO

# (1.1) run_tracking.py
# main script that runs basf2 tracking tasks yielding performance metrics in a CSV file
| main() # handles SVD-only tracking, standard basf2 reconstruction
| │
| ├── Setup full tracking chain
| ├── Load ToCDCCKF parameter set from json file
| ├── Inject parameters into ToCDCCKF module
| ├── Add modules to calculate tracking metrics, write to a CSV file
| ├── Write tracking metrics to a CSV file
└ └── Terminate Tracking

# (1.2) run_tracking_svd.py
# main script that runs basf2 tracking tasks yielding performance metrics in a CSV file
| main() # handles SVD-only tracking, standard basf2 reconstruction
| │
| ├── Setup SVD-only tracking chain
| ├── Load ToCDCCKF parameter set from json file
| ├── Inject parameters into ToCDCCKF module
| ├── Add modules to calculate tracking metrics, write to a CSV file
| ├── Write tracking metrics to a CSV file
└ └── Terminate Tracking
```

For post analysis, we use the _`ana_grid.py`_ script that reads all CSV files, combine them and select the best parameters.

```shell
# (2) ana_grid.py
# main script for post analysis on metrics
| main()
| │
| ├── Reads CSV file with tracking metrics
| ├── Aggregates metrics (if not done already)
| ├── Select and save best parameters (json file)
| ├── Plots tracking metrics
└ └── Terminates analysis
```



### _Key Hyperparameters_

The following parameters in the `ToCDCCKF` module can be optimized:

- _`maximalDeltaPhi`_: Maximal distance in $\phi$ between wires for $z=0$ plane
- _`maximalLayerJump`_: Maximal jump over $N$ layers
- _`minimalPtRequirement`_: Minimal $p_T$ requirement for the input tracks
- _`pathMaximalCandidatesInFlight`_: Maximum number of candidates in flight
- _`stateMaximalHitCandidates`_: Maximum number of hit candidates per state



### _Performance Metrics_

The optimization is based on two key metrics:
- **Hit Efficiency**: The ratio of correctly found hits to total true hits
- **Hit Purity**: The ratio of correctly found hits to total found hits
- **Track Efficiency**: The ratio of correctly found tracks to total true tracks
- **Track Purity**: The ratio of correctly found tracks to total found tracks

A combined score is calculated as: `score = 0.6 * efficiency + 0.4 * purity ?`.



### _Handy Scripts to Run HPO_

```bash
# LSF Cluster
$ bsub < run_grid_lsf.sh

# Resubmit failed workers, first clean the failed jobs e.g.
./resubmit_job_lsf.sh 92 91 98 89 86 81

# Second, submit failed jobs
bsub -J "grid[92,91,98,89,86,81]" < run_grid_lsf.sh
```

```bash
# Local
python3 run_grid.py
```



### _Service Task_

- improve the SVD to CDC CKF in terms of efficiency and purity
- investigate how to improve the SVD to CDC CKF so that one can recover inefficiencies in the CDC track finding, caused by hardware issues in the readout of the CDC.
- [Tracking GitLab issue #227](https://gitlab.desy.de/belle2/software/tracking/issues/-/issues/227)
