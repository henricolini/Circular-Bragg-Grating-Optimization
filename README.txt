Lumerical Simulation Framework – Thesis Tools
=============================================

This codebase is a modular framework for setting up, running, and analyzing electromagnetic simulations (FDTD and FDE) using Lumerical software. It is designed for optimizing nanophotonic structures (e.g., bullseye cavities) via Universal and Bayesian methods.

------------------------------------------------------------

Project Structure
-----------------

- main.py          
  Central execution script. Sets up materials, configures simulations, and runs tests or optimizations.

- Classes.py       
  Contains core classes:
    • Universal_Design: Runs simulations and optimization.
    • LumericalFDTDSetup: Builds geometries and imports materials.

- Launcher.py      
  Launches simulations remotely via SSH to a DTU computing cluster.

- SSHHandler.py    
  Manages SSH connections, file transfers, and job submission using `paramiko` and `scp`.

- get_results.py   
  Utility to extract and plot results (Purcell factor and collection efficiency) from completed .fsp files.

------------------------------------------------------------

Dependencies
------------

Python packages:
- numpy
- matplotlib
- pandas
- scikit-optimize
- paramiko
- scp
- pyqt5

Other requirements:
- Lumerical software installed (FDTD & MODE Solutions)
- Lumerical Python API accessible in `sys.path`
- HPC cluster access (e.g., DTU cluster with LSF)

------------------------------------------------------------

How It Works
------------

1. Material Setup:
   - Material optical data (n, k) is imported from CSV.
   - Optional anisotropic merging of ordinary/extraordinary indices.

2. Simulation Setup:
   - Geometry and simulation regions created via `setup_simulation_fdtd()` and `setup_simulation_fde()`.

3. Running Simulations:
   - Run locally or remotely depending on `local` and `run` flags.
   - Remote jobs are submitted using `Launcher` and cluster scripts.

4. Optimization:
   - Universal Simulation: Adjusts design to match target wavelength.
   - Bayesian Optimization: Tunes geometric parameters to maximize Purcell factor and collection efficiency.

5. Result Analysis:
   - Extract simulation data from .fsp file with `get_results.py`.
   - Plots spectra and prints structure parameters.

------------------------------------------------------------

Usage Example
-------------

In main.py:
--------------
Set the main parameters for your specific simulation, such as:
- target wavelength
- number of rings
- dipole height
- material file paths
- fixed parameters

Then configure the run mode:
run = True           # Set to True to launch simulations
local = False        # Set to True to run locally instead of on the cluster

Then run:
--------------
python main.py       # Sets up and runs the simulation

To analyze existing simulation results:
--------------
python get_results.py       # Plots Purcell factor & collection efficiency from .fsp file

