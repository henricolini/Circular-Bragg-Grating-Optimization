# -*- coding: utf-8 -*-
"""
Created on Tue Mar 18 11:16:51 2025

@author: kikos
"""
import os
from Classes import Universal_Design, LumericalFDTDSetup
from Launcher import Launcher

run=True # set run to True for full optimization
local=False# if you want to run locally on your computer switch to True and ignore username and host

username="s232666" # username for cluster
host="login2.gbar.dtu.dk" # dtu cluster
directory_on_cluser=r"/zhome/05/6/202876/Desktop/test" # directory on cluster to run the files
launch = Launcher(username,host,directory_on_cluser) if (not local and run) else None

# Download csv file from https://refractiveindex.info/ if the material is not anisotropic just set one of the variables to None
material_cavity_o=r"C:\Users\kikos\Desktop\Faculdade\5 ano\Master Thesis\Simulations\Materials\h-BN\Zotev-o.csv"
material_cavity_e=r"C:\Users\kikos\Desktop\Faculdade\5 ano\Master Thesis\Simulations\Materials\h-BN\Zotev-o.csv"
material_name="hBN" # name of the material in lumerical

target_wavelegth=0.750e-6 # wavelegth for which you want to optimise for

num_modes=10 # how many modes you want FDE to calculate
chosen_mode=1 # mode it chooses to optimise for

number_of_iterations=20 # how many iterations of the bayesian op
# here you can create constraints to the simulation, if {} no constraint
fixed_parameters = {
    #     "height_cavity": 0,
        "height_substract": 209e-9,
    #     "n_rings": 0,
    #     "radius_mesa": 0,
    #     "ring_period": 0,
    #     "duty_cycle": 0
    }

# Save to a specific folder
save_folder = r"D:\Master thesis files\Simulations\Data\Gold\h-BN_Mid\Test\saved" #save folder on local computer
cavity_file_name="hBN_optimization_750nm_2try" # file name


#######################################################################################################################################################
data_cavity=[material_cavity_o,material_cavity_e]

filename_FDTD = os.path.join(save_folder, cavity_file_name+".fsp")
filename_FDE= os.path.join(save_folder, cavity_file_name+".lms")

#sets up FDE Simulation and FDTD
setup_sim = LumericalFDTDSetup(save_folder,material_name, data_cavity, target_wavelegth)  # Define cavity material
setup_sim.setup_simulation_fdtd(save_folder, cavity_file_name+".fsp")
setup_sim.setup_simulation_fde(save_folder, cavity_file_name+".lms")

#Runs the main code
simulation = Universal_Design(filename_FDTD, filename_FDE, target_wavelegth, local, run, username, host, fixed_parameters, launch, material_name)
if run is True:
    simulation.Universal_Simulation(num_modes,chosen_mode)
    simulation.Bayesian_Optimization(number_of_iterations)
    simulation.run_simulation_FDTD(accuracy=4)
    print("Simulation Finished")
else:
    simulation.run_simulation_FDE(target_wavelegth,num_modes,chosen_mode)
    simulation.run_simulation_FDTD()
    print("Parameters are set")