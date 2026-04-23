# _ToCDCCKF Optimization_

The tracking parameters can be optimized using the Grid Search (_`run_grid.py`_) approachs both locally and on cluster. Since we have no access to _`basf2`_ internals during the optimization, we only rely on `tracking efficiency`, `tracking purity`, `hit efficiency`, and `hit purity` metrics saved to a CSV file. This is called a **_Black Box Optimization_** approach, where special librraries like **_Optuna_**, **_RayTune_**, **_Ax_**, **_SMAC_**, **_HEBO_**, **_Hyperopt_**, **_Skopt_**, **_Nevergrad_**, , etc can be used. However, we rely on python scientific stack (NumPy, Pandas, SciPy, etc). This choice made the optimization workflow complicated. In anycase, we have worker-specific workflow where each worker runs trials/chucks assigned to it independently. Once all workers are done, we aggregate the results and select the best parameters based on `F1-score`.


## _1. Simulation & Reconstruction_

Several standard scripts are available to run simulation and reconstruction usually named as _`start_<name>.py`_. For example,

1. _`start_gen.py`_: Run generation (_`xxx_gen.root`_)
2. _`start_mcri.py`_, _`start_mcrd.py`_, _`start_sim.py`_: Run simulation (_`xxx_mcri.root`, `xxx_mcrd.root`, `xxx_sim.root`_)
3. _`start_rec.py`_: Run tracking reconstruction (_`xxx_mdst.root`_)

We can combine _`1`_ and _`2`_ into simulation scripts, and _`3`_ into reconstruction script for convenience. In reality, all steps can be combined into single script performing generation, simulation and reconstruction all at once. There is a handy _`bash`_ script to run _`basf2`_ scripts called _`start_all.sh`_. In my scheme, I perform simulation (_`2`_) and reconstruction (_`3`_) separately so the later expect `RootInput` from the former. All scripts has default arguments _`argparse`_ that are worth to look at before running these scripts.

- To run **_simulation (`2`)_**, we need two arguments _`--output`_ and _`--finalstates`_ with defaults as _`dataset/mixed_mcri.root`_ and _`mixed`_. Handy command with defaults is as follows:

```shell
# run simulation (mcri: run-independent, mcrd: run-dependent, sim: run-dependent with custom payloads)
basf2 start_mcri.py > "dataset/start_mcri.log" 2>&1
```

- To run **_reconstruction (`3`)_**, we need two arguments _`--input`_ and _`--output`_  with defaults as _`dataset/mixed_mcri.root`_ and _`dataset/mixed_mdst.root`_. Handy command with defaults is as follows:

```shell
# run reconstruction
basf2 start_rec.py > "dataset/start_rec.log" 2>&1
```

The separation of simulation and reconscturction is requiremnet for optimization of _`ToCDCCKF`_ where a single simulation output could be used for reconstruction again and again during optimization with different parameters to _`ToCDCCKF`_.


## _2. Grid Search Optimization_

Once we have a output from simulation, we can now run GridSearch optimizaiton. There are three main scripts: _`run_grid.py`_, _`run_tracking_svd.py`_ and _`ana_grid.py`_. The _`run_grid.py`_ is steering script that runs _`run_tracking_svd.py`_ for a unique set of parameters for _`ToCDCCKF`_ algorithm. Once, the optimization is finished the _`ana_grid.py`_ perform post analysis on outputs from each parameter set. The additional code is located in _`src/`_.


For optimization, run _`run_grid.py`_:

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

# (1.1) run_tracking_svd.py
# main script that runs basf2 tracking tasks yielding performance metrics in a CSV file
| main()
| │
| ├── Setup SVD-only tracking chain
| ├── Load ToCDCCKF parameter set from json file
| ├── Inject parameters into ToCDCCKF module
| ├── Add modules to calculate tracking metrics, write to a CSV file
| ├── Write tracking metrics to a CSV file
└ └── Terminate Tracking
```

For post analysis, use _`ana_grid.py`_ script:

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

The following parameters in the _`ToCDCCKF`_ module can be optimized:

- _`maximalDeltaPhi`_: Maximal distance in $\phi$ between wires for $z=0$ plane
- _`maximalLayerJump`_: Maximal jump over $N$ layers
- _`minimalPtRequirement`_: Minimal $p_T$ requirement for the input tracks
- _`pathMaximalCandidatesInFlight`_: Maximum number of candidates in flight
- _`stateMaximalHitCandidates`_: Maximum number of hit candidates per state

For _`run_grid.py`_, the parameters space (_`PARAM_SPACE`_) is set in _`src/optimization_utils.py`_ as follows:

```shell
# parameter ranges for run_grid.py
PARAM_SPACE = {
    "maximalDeltaPhi": [0.2, 0.4, 0.5],  # default: 0.3926990
    "maximalLayerJump": [4, 5, 6, 7, 8],  # default: 4
    "minimalPtRequirement": [0.0, 0.1],  # default: 0
    "pathMaximalCandidatesInFlight": [3, 4],  # default: 3
    "stateMaximalHitCandidates": [3, 4, 5],  # default: 4
}
```


### _Performance Metrics_

The optimization is based on two key metrics:

- **Hit Efficiency**: The ratio of correctly found hits to total true hits
- **Hit Purity**: The ratio of correctly found hits to total found hits

We build an **F1 Score** from hit efficiency and hit purity to have a single optimization objective. In GridSearch, optimization is not derived by `F1` as we explore whole parameter space anyway. However, it is espcailly important if RandomSearch or BayesianOtimization are intended instead of GridSearch:

```shell
# F1 Score
f1 = (2 * hit efficiency * hit purity) / (hit efficiency + hit purity)
```

### _Handy Scripts to Run HPO_

```bash
# LSF Cluster, user need to mention number of jobs to add
$ bsub < run_grid_lsf.sh

# Resubmit failed workers, it clean the failed jobs and provide resubmission command
./resubmit_job_lsf.sh 92 91 98 89 86 81

# resubmission command
bsub -J "grid[92,91,98,89,86,81]" < run_grid_lsf.sh
```

In most cases, one does not need any resubmission if the _`#BSUB -J "grid[1-18]"`_ is setup wisely i.e. the choice of _`PARAM_SPACE`_ produces hundreds of grid points if cluster jobs are less then each job has to handle larger chunk of these grid points. By increasing the jobs from 18 to 100 means each job has less grid point in its chunk and thus finish faster before risking failure from cluster computing restrictions.


```bash
# Local
python3 run_grid.py
```


### _Service Task_

- improve the SVD to CDC CKF in terms of efficiency and purity
- investigate how to improve the SVD to CDC CKF so that one can recover inefficiencies in the CDC track finding, caused by hardware issues in the readout of the CDC.
- [Tracking GitLab issue #227](https://gitlab.desy.de/belle2/software/tracking/issues/-/issues/227)
