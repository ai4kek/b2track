# Belle II Tracking

Playground for Belle II Tracking.

## _`basf2` Track Reconstruction_

The tracking reconstruction workflow is as follows:

1. _`start_gen.py`_: Run generators (_`gen.root`_)
2. _`start_mcri.py`_, or _`start_mcrd.py`_: Run simulation (_`sim.root`_)
3. _`start_rec.py`_: Run tracking reconstruction (_`rec.root`_ or _`mdst.root`_)

In reality, most of the time we combine 1 and 2 into one step. One can run all steps in one go by running _`start_all.sh`_:


```shell
#!/bin/bash

# from local cvmfs
source /cvmfs/belle.cern.ch/tools/b2setup release-08-03-00

# run generator
basf2 start_gen.py > "dataset/start_gen.log" 2>&1
echo "start_gen.py script executed successfully..."

# run simulation
basf2 start_sim.py > "dataset/start_sim.log" 2>&1
echo "start_sim.py script executed successfully..."

# run reconstruction
basf2 start_rec.py > "dataset/start_rec.log" 2>&1
echo "start_rec.py script executed successfully..."
```

If no arguments are provided (_`argparse`_), then all scripts will use the default values. To see how to inject ToCDCCKF parameters, see the _`run_tracking.py`_ or _`run_tracking_svd.py`_ scripts.


## _`basf2` Track Validation_

Once we have the best parameters, we can validate them by runing full tracking chain with the best parameters. For this purpose, all we need is a simulation file e.g. `mixed_sim.root` and run full tracking chain with the original parameters and the optimized parameters. In the  end we can run analysis-level validation to get tracking efficiency and purity metrics.


- run simulation
- run full tracking chain with original parameters
- run track validation
- compare mertrics for original and optimized parameters










## _`basf2` Workflow_

There are three steps:

- _`Event Generation` (EvtGen, KKMC, Particle Gun, etc)_
- _`Detector Simulation` (Particle Interactions + Signal Digitization)_
- _`Reconstruction` (Tracks + Clusters)_

There are two ways to create a steering files based on adding modules directly, or indirectly:

- _Direct: `main = basf2.Path`, `main.add_module()` or `basf2.some_module (path=main)`, `basf2.Process()`, etc._
- _Indirect: `module = basf2.register_module("Moduel Name")`, `module.Param("Param Name", "Values")`, `main = basf2.create_path()`, `main.add_module(module)`, `basf2.Process()`, etc._


## _`basf2` Reconstruction Flow_

### _1. Real Reconstruction_

```shell
# Top-level Reconstruction Function and Calls
| add_reconstruction()
| │
| ├── add_prefilter_reconstruction()
| │ ├── add_prefilter_pretracking_reconstruction()   # Clustering
| │ ├── add_prefilter_tracking_reconstruction()      # Tracking essential for HLT filter calculation
| │ └── add_prefilter_posttracking_reconstruction()  # PID and clustering essential for HLT
| │ 
| ├── add_postfilter_reconstruction()
| │ ├── add_postfilter_tracking_reconstruction()     # Rest of the tracking
| │ └── add_postfilter_posttracking_reconstruction() # Rest of PID and clustering
| │
| └── plus the modules to calculate the software trigger cuts.
```

### _2. MC Reconstruction_

```shell
# Top-level MC Reconstruction Function and Calls
| add_mc_reconstruction()
| ├── add_prefilter_pretracking_reconstruction()
| ├── add_mc_tracking_reconstruction()
| └── add_posttracking_reconstruction()
```

### _3. Cosmic Reconstruction_

```shell
# Top-level Cosmic Reconstruction Function and Calls
| add_cosmics_reconstruction()
| ├── add_prefilter_pretracking_reconstruction()
| ├── add_cr_tracking_reconstruction()
| └── add_posttracking_reconstruction()
```

## _`basf2` Track Reconstruction Flow_

Main tracking functions as part of reconstruction task comes from the top-level `path/to/basf2/tracking/` module of the `basf2`:

```shell
# Tracking Functions
| add_tracking_reconstruction()     # Real Tracking
| │
| ├── add_prefilter_tracking_reconstruction()
| │   │
| │   ├── add_track_finding()
| │   │   ├── add_cdc_track_finding()
| │   │   ├── add_svd_track_finding()     # use_svd_to_cdc_ckf: SVDToCDCCKF ("ToCDCCKF")
| │   │   ├── add_pxd_track_finding()
| │   │   └── add_eclcdc_track_finding()  # use_ecl_to_cdc_ckf: ECLToCDCCKF ("T0CDCCKF") 
| │   ├── add_mc_track_finding()
| │   │
| ├── add_postfilter_tracking_reconstruction()
| │
| add_mc_tracking_reconstruction()  # MC Tracking
| add_cr_tracking_reconstruction()  # Cosmic Tracking
```

The difference between _`add_reconstruction()`_ and _`add_tracking_reconstruction()`_ is only additional modules to calculate the software trigger cuts which are added in the _`add_reconstruction()`_. So for track reconstruction only, one can simply use _`add_tracking_reconstruction()`_.


## _`basf2` Development_

```shell
# create feature branch from main
git branch -b feature/227-improve-svd-to-cdc-ckf

# setup upstream
git push --set-upstream origin feature/227-improve-svd-to-cdc-ckf

# switch to your branch
git checkout feature/227-improve-svd-to-cdc-ckf

# rebase with main
git fetch --all && git merge origin/main

# push to remote
git push
```


## _`b2display` Path Settings_

```bash
# fix for evtdisplay
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
```
