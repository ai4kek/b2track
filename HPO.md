
## _Hyperparameter Optimization (HPO)_

The tracking parameters can be optimized using the Grid Search (_`run_grid.py`_) and the Random Search (_`run_rand.py`_) approachs both locally and on cluster. Since we have no access to _`basf2`_ internals during the optimization, we only rely on tracking efficiency, tracking purity, hit efficiency, and hit purity metrics saved to a CSV file. This is called a **_Black Box Optimization_** approach, where special librraries like **_Optuna_**, **_RayTune_**, **_Ax_**, **_SMAC_**, **_HEBO_**, **_Hyperopt_**, **_Skopt_**, **_Nevergrad_**, , etc can be used, however, we rely on python scientific stack (NumPy, Pandas, SciPy, etc). This choice made the optimization workflow complicated. In anycase, we have worker-specific workflow where each worker runs a trials assigned to it independently. Once all workers are done, we aggregate the results and select the best parameters based on F1 score.


### _Grid Search Workflow_

To run exhaustive grid search, we use the _`run_grid.py`_  script. The flow of the script is as follows:

```shell
# (1) run_grid.py
# main steering script that handles parallelization, chunking, and aggregation
| main()
| │
| ├── selects execution mode (single or multi-worker, cluster)
| ├── splits the parameter space and creates chunks of trials
| ├── distirbutes chunks to workers
| ├── run process_chunk() # processes trials one by one in the chunk
| │   ├── trial_objective()  # handles one trial at a time
| │   │   └── run_tracking_with_params() # runs basf2 tracking
| │   │     └── run_tracking_svd.py  # SVD-only or Full (run_tracking.py)
| │   └── finish trials in a chunk
| └── (optional) aggregate metrics into a single CSV file
| └─ terminate HPO
|
|
# (1.1) run_tracking_svd.py
# main script that runs basf2 tracking tasks yielding performance metrics in a CSV file
| main() # handles SVD-only tracking, standard basf2 reconstruction
| │
| ├── Setup SVD-only tracking
| ├── Load ToCDCCKF parameter set from json file
| ├── Inject parameters into ToCDCCKF module
| ├── Add modules to calculate tracking metrics, write to a CSV file
| ├── Write tracking metrics to a CSV file
| └── Terminate Tracking
|
|
# (2) ana_grid.py
# main script for post analysis on metrics
| main()
| │
| ├── reads CSV file with tracking metrics
| ├── aggregates metrics (if not done already), 
| ├── select and save best parameters (json file)
| ├── plots tracking metrics
| └── terminates analysis
```

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

For post analysis, we use the _`ana_grid.py`_ script that reads all CSV files, combine them and select the best parameters.


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

A combined score is calculated as: `score = 0.6 * efficiency + 0.4 * purity ?`



### _Validation of HPO_

Once we have the best parameters, we can validate them by runing full tracking chain with the best parameters. For this purpose, all we need is a simulation file e.g. `mixed_sim.root` and run full tracking chain with the original parameters and the optimized parameters. In the  end we can run analysis-level validation to get tracking efficiency and purity metrics.


- run simulation
- run full tracking chain with original parameters
- run track validation
- compare mertrics for original and optimized parameters




## _Tracking Reconstruction Workflow_

The tracking reconstruction workflow is as follows:

- _`start_gen.py`_: Run generators
- _`start_mcri.py`_, or _`start_mcrd.py`_: Run simulation
- _`start_rec.py`_: Run tracking reconstruction

One can run all three in the same time by running _`start_all.sh`_.