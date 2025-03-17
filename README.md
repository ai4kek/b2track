# Belle II Tracking

Playground for Belle II Tracking.

## _`basf2` Workflow_

There are three steps:

- _`Event Generation` (EvtGen, Particle Gun, etc)_
- _`Detector Simulation` (Particle Interactions + Signal Digitization)_
- _`Reconstruction` (Tracks + Clusters)_

There are two ways to create a steering file: direct, and indirect.

- _Direct: `main = basf2.Path`, `main.add_module()` or `basf2.some_module (path=main)`, `basf2.Process()`, etc._
- _Indirect: `module = basf2.register_module("Moduel Name")`, `module.Param("Param Name", "Values")`, `main = basf2.create_path()`, `main.add_module(module)`, `basf2.Process()`, etc._


### _`basf2` Development_

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

## _Service Task_

- improve the SVD to CDC CKF in terms of efficiency and purity
- investigate how to improve the SVD to CDC CKF so that one can recover inefficiencies in the CDC track finding, caused by hardware issues in the readout of the CDC.
- [Tracking GitLab issue #227](https://gitlab.desy.de/belle2/software/tracking/issues/-/issues/227)


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

The difference between `add_reconstruction()` and `add_tracking_reconstruction()` is only additional modules to calculate the software trigger cuts which are added in the `add_reconstruction()`. So for track reconstruction only, one can simply use `add_tracking_reconstruction()`. For example,

```shell
#!/usr/bin/env python3

##########################################################################
# basf2 (Belle II Analysis Software Framework)                           #
# Author: The Belle II Collaboration                                     #
#                                                                        #
# See git log for contributors and copyright holders.                    #
# This file is licensed under LGPL-3.0, see LICENSE.md.                  #
##########################################################################

import basf2 as b2
import generators as ge
import mdst
import reconstruction as re
import simulation as si
import tracking as trkx


main = b2.Path()

# Add RootInput
main.add_module("RootInput", inputFileName="mixed_sim.root")

# Add full reconstruction
# re.add_reconstruction(path=main)

# Add full tracking reconstuction
trkx.add_tracking_reconstruction(
    path=main,
    components=None,
    pruneTracks=False,
    mcTrackFinding=False,
    skipGeometryAdding=False,
)

# Create the mDST output file
additional_br = []
outFile = "mdst_reco.root"
mdst.add_mdst_output(
    path=main,
    mc=True,
    filename=outFile,
    additionalBranches=additional_br,
    dataDescription=None,
)

b2.process(main)
print(b2.statistics)
```