# Belle II Tracking

Playground for Belle II Tracking.

## Belle II Workflow

There are three steps:

- _`Event Generation` (EvtGen, Particle Gun, etc)_
- _`Detector Simulation` (Particle Interactions + Signal Digitization)_
- _`Reconstruction` (Tracks + Clusters)_

There are two ways to create a steering file: direct, and indirect.

- _Direct: `main = basf2.Path`, `main.add_module()` or `basf2.some_module (path=main)`, `basf2.Process()`, etc._
- _Indirect: `module = basf2.register_module("Moduel Name")`, `module.Param("Param Name", "Values")`, `main = basf2.create_path()`, `main.add_module(module)`, `basf2.Process()`, etc._

## Belle II Display

```bash
# fix for evtdisplay
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
```

## Service Task

- improve the SVD to CDC CKF in terms of efficiency and purity
- investigate how to improve the SVD to CDC CKF so that one can recover inefficiencies in the CDC track finding, caused by hardware issues in the readout of the CDC.
- [Tracking GitLab issue #227](https://gitlab.desy.de/belle2/software/tracking/issues/-/issues/227)

### Development Workflow

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


