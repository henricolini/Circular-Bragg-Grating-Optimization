# -*- coding: utf-8 -*-
"""
Created on Tue Mar 18 11:16:51 2025

@author: kikos
"""
import os
import datetime
from Classes import Universal_Design, LumericalFDTDSetup
from Launcher import Launcher

#Fill this to run the optimization

run=True # set run to True for full optimization, False only creates the files
local=False# if you want to run locally on your computer switch to True and ignore username and host

username="s232666" # username for cluster
host="login2.gbar.dtu.dk" # dtu cluster
directory_on_cluser=r"/zhome/05/6/202876/Desktop/test" # directory on cluster to run the files
launch = Launcher(username,host,directory_on_cluser) if (not local and run) else None

# Download csv file from https://refractiveindex.info/ if the material is not anisotropic just set one of the variables to None
material_cavity_o=r"C:\Users\kikos\Desktop\Faculdade\5 ano\Master Thesis\Simulations\Materials\h-BN\Zotev-o.csv"
material_cavity_e=r"C:\Users\kikos\Desktop\Faculdade\5 ano\Master Thesis\Simulations\Materials\h-BN\Zotev-e.csv"

emmiter_o=r"C:\Users\kikos\Desktop\Faculdade\5 ano\Master Thesis\Simulations\Materials\WSe2\Munkhbat-o.csv"
emmiter_e=r"C:\Users\kikos\Desktop\Faculdade\5 ano\Master Thesis\Simulations\Materials\WSe2\Munkhbat-e.csv"

material_name="hBN" # name of the material in lumerical
emmiter_name="WSe2"

target_wavelegth=0.750e-6 # wavelegth for which you want to optimise for
dipole_height=0.8e-6 # height of the dipole

num_modes=10 # how many modes you want FDE to calculate
chosen_mode=1 # mode it chooses to optimise for

number_of_iterations=0 #how many iterations of the bayesian optimization

layer=False #set to true if want to add 2D layer and mesh override, it increses the simulation time a lot
holes=False

# here you can create constraints to the simulation, if {} no constraint
fixed_parameters = {
        "height_cavity": 324e-9,
        "height_substrate": 210e-9,
    #     "n_rings": 0,
    #     "radius_mesa": 0,
    #     "ring_period": 0,
    #     "duty_cycle": 0
    }

# Save to a specific folder
save_folder = r"D:\Master thesis files\Simulations\Data\Gold\Dummy_reflectivity" #save folder on local computer
cavity_file_name="dummy_reflecticity_measurment" # file name


#######################################################################################################################################################
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
cavity_file_name = f"{cavity_file_name}_{target_wavelegth*10e8:.0f}nm_{timestamp}"
data_materials=[material_cavity_o,material_cavity_e,emmiter_o,emmiter_e]

# creates the files in the save folders
filename_FDTD =r"D:\Master thesis files\Simulations\Data\Gold\Dummy_reflectivity\dummy_reflecticity_measurment_750nm_20250501_144645.fsp" #os.path.join(save_folder, cavity_file_name+".fsp")
filename_FDE= r"D:\Master thesis files\Simulations\Data\Gold\Dummy_reflectivity\dummy_reflecticity_measurment_750nm_20250501_144645.lms"#os.path.join(save_folder, cavity_file_name+".lms")


# #sets up FDE Simulation and FDTD
# setup_sim = LumericalFDTDSetup(save_folder,material_name,emmiter_name, data_materials, target_wavelegth, layer, holes)  # Define cavity material
# setup_sim.setup_simulation_fdtd(save_folder, cavity_file_name+".fsp")
# setup_sim.setup_simulation_fde(save_folder, cavity_file_name+".lms")

#Runs the main code
simulation = Universal_Design(filename_FDTD, filename_FDE,  target_wavelegth, dipole_height, local, run, username, host, fixed_parameters, launch, material_name,holes)
if run is True:
    # simulation.Universal_Simulation(num_modes,chosen_mode)
    # simulation.Bayesian_Optimization(number_of_iterations)
    simulation.run_simulation_FDTD(accuracy=1)
    print("Simulation Finished")
else:
    simulation.run_simulation_FDE(target_wavelegth,num_modes,chosen_mode)
    simulation.run_simulation_FDTD()
    print("Parameters are set")