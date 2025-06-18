# -*- coding: utf-8 -*-
"""
Created on Tue Mar 18 11:16:03 2025

@author: kikos
"""

import sys
import os
#default path for current release 
sys.path.append(r"D:\Master thesis files\Lumerical\api\python") 
sys.path.append(os.path.dirname(__file__)) #Current directory
import lumapi
import matplotlib.pyplot as plt
import numpy as np
from skopt import Optimizer
from skopt.space import Real, Integer
import pandas as pd
import csv

C = 299792458  # Speed of light


class Universal_Design:
    def __init__(self, filenameFDTD,filenameFDE, target_wavelength, dipole_height, local, run, username, host, fixed_parameters, launch, material_name,holes,angle):
        self.filename_FDTD = filenameFDTD
        self.filename_FDE= filenameFDE
        self.local = local
        self.run = run
        self.material_name=material_name
        self.dipole_height=dipole_height
        self.holes=holes
        self.angle=angle

        self.weight_purcell = 0.5
        self.weight_collection = 0.5
        self.max_purcell = 3
        self.max_collection = 1
        self.all_scores=[]
        
        self.change_in_param = 0.5
        self.change_in_ring = 2
        
        # Default parameters
        self.parameters = {
            "height_cavity": 0.3516e-6,
            "height_substrate": 0.21e-6,
            "n_rings": 5,
            "radius_mesa": 0.4443e-6,
            "ring_period": 0.4179e-6,
            "duty_cycle": 0.7,
            "material": material_name,
            "hole_diameter":0.135e-6 ,
            "spacing": 0.210e-6 
            }
        
        self.target_wavelength = target_wavelength
        self.step_wavelength = 0.100e-6
        self.step_universal = 0.100e-6
        self.wavelengths = (
            self.target_wavelength,
            self.target_wavelength - self.step_wavelength,
            self.target_wavelength + self.step_wavelength
        )
        
        self.launch = launch
        
        self.fixed_parameters = fixed_parameters  # Will store fixed parameters
        
    def set_parameters(self, new_parameters=None):
        """
        Update parameters, respecting the fixed ones.
    
        :param new_parameters: Dictionary of parameters to update
        :param fixed_parameters: Dictionary of parameters to fix (optional)
        """
        if new_parameters is None:
            new_parameters = {}
    
        # Store fixed parameters and set their values
        for key, value in self.fixed_parameters.items():
            if key in self.parameters:
                self.parameters[key] = value
    
        # Update non-fixed parameters
        for key, value in new_parameters.items():
            if key in self.parameters and key not in self.fixed_parameters:
                self.parameters[key] = value

                               
    def run_simulation_FDE(self,target_wv,num_modes,chosen_mode):
        #Open the Lumerical MODE simulation file
        fde = lumapi.MODE(filename=self.filename_FDE)
        
        # Switch to layout mode to modify structure parameters
        fde.switchtolayout()
        
        self.set_parameters()
        
        # Set the height of the cavity layer
        fde.setnamed("cavity", "height", self.parameters["height_cavity"])
        fde.setnamed("cavity", "material", self.parameters["material"])
        
        # Set the height of the substrate layer
        fde.setnamed("substrate", "h_sio2", self.parameters["height_substrate"])
        
        # Set parameters for FDE region
        fde.setnamed("FDE","solver type",2);
        fde.setnamed("FDE","x",0);
        fde.setnamed("FDE","x span",2 * (self.parameters["radius_mesa"] + (self.parameters["ring_period"] * self.parameters["n_rings"])) + 1e-6);
        fde.setnamed("FDE","z",0);
        fde.setnamed("FDE","z max",self.parameters["height_cavity"]+0.1e-6);
        fde.setnamed("FDE","z min", -(self.parameters["height_substrate"] + 0.15e-6));
        fde.setnamed("FDE","y",0);
        
        try:
            fde.setnamed("layer", "z", self.dipole_height-0.001e-6)
            fde.setnamed("layer", "r_ring", self.parameters["ring_period"])
            fde.setnamed("layer", "r_circle", self.parameters["radius_mesa"])
            fde.setnamed("layer", "duty_cycle", self.parameters["duty_cycle"])
            fde.setnamed("layer", "n_rings", self.parameters["n_rings"])
        except:
            pass
        # Set the number of trial modes for the mode solver
        fde.setnamed("FDE", "number of trial modes", num_modes)  # Define how many modes to search for
        
        # Set the wavelength at which the modes will be solved
        fde.setnamed("FDE", "wavelength", target_wv)  # Define the operating wavelength

        
        if self.run is True:
            # Run the simulation
            fde.run()
        
            # Find eigenmodes of the structure
            fde.findmodes()
            
            # Retrieve the effective refractive index of the first mode
            neff = np.real(fde.getdata(f"mode{chosen_mode}", "neff"))
        
            # Close the MODE solver session
            fde.save()
            fde.close()

            return neff
        
        else:
            # Close the MODE solver session
            fde.save()
            fde.close()
            return None
    def run_simulation_FDTD(self, accuracy=1, universal=False, bayesian=False, profile=1):
        fdtd = lumapi.FDTD(filename=self.filename_FDTD)
        fdtd.switchtolayout()
        
        try:
            self.set_parameters()
            
            if self.dipole_height == None:
                h_source=self.parameters["height_cavity"]/2
            else:
                h_source = self.dipole_height
            
            try:
                # Set simulation parameters without holes
                fdtd.setnamed("cavity", "height", self.parameters["height_cavity"])
                fdtd.setnamed("cavity", "r_ring", self.parameters["ring_period"])
                fdtd.setnamed("cavity", "r_circle", self.parameters["radius_mesa"])
                fdtd.setnamed("cavity", "duty_cycle", self.parameters["duty_cycle"])
                fdtd.setnamed("cavity", "n_rings", self.parameters["n_rings"])
                fdtd.setnamed("cavity", "material", self.parameters["material"])
                
            except:
                pass
            try:
                # Set simulation parameters with holes
                fdtd.setnamed("cavity", "height", self.parameters["height_cavity"])
                fdtd.setnamed("cavity", "ring_period", self.parameters["ring_period"])
                fdtd.setnamed("cavity", "radius_mesa", self.parameters["radius_mesa"])
                fdtd.setnamed("cavity", "n_rings", self.parameters["n_rings"])
                fdtd.setnamed("cavity", "material", self.parameters["material"])
                fdtd.setnamed("cavity", "hole_diameter", self.parameters["hole_diameter"])
                fdtd.setnamed("cavity", "spacing", self.parameters["spacing"])
            except:
                pass
            try:
                fdtd.setnamed("layer", "z", h_source-0.001e-6)
                fdtd.setnamed("layer", "r_ring", self.parameters["ring_period"])
                fdtd.setnamed("layer", "r_circle", self.parameters["radius_mesa"])
                fdtd.setnamed("layer", "duty_cycle", self.parameters["duty_cycle"])
                fdtd.setnamed("layer", "n_rings", self.parameters["n_rings"])
            except:
                pass
            
            fdtd.setnamed("cavity", "angle_trench", self.angle)
            fdtd.setnamed("substrate", "h_sio2", self.parameters["height_substrate"])
            
            fdtd.setnamed("source", "z", h_source)
            
            fdtd.setnamed("FDTD", "x span", 2 * (self.parameters["radius_mesa"] + (self.parameters["ring_period"] * self.parameters["n_rings"])) + 1e-6)
            fdtd.setnamed("FDTD", "y span", 2 * (self.parameters["radius_mesa"] + (self.parameters["ring_period"] * self.parameters["n_rings"])) + 1e-6)
            fdtd.setnamed("FDTD", "z min", -(self.parameters["height_substrate"] + 0.15e-6))
            fdtd.setnamed("FDTD", "z max", (self.parameters["height_cavity"] + 0.5e-6))
            fdtd.setnamed("FDTD", "mesh accuracy", accuracy)
            fdtd.setnamed("FDTD", "pml profile", profile)
            
            fdtd.setnamed("analysis group", "z", h_source) #+ 1e-9)
            fdtd.setnamed("analysis group", "x_span_prof",2 * (self.parameters["radius_mesa"] + (self.parameters["ring_period"] * self.parameters["n_rings"])))
            fdtd.setnamed("analysis group", "y_span_prof", 2 * (self.parameters["radius_mesa"] + (self.parameters["ring_period"] * self.parameters["n_rings"])))
            
            if universal is True:
                fdtd.setnamed("source", "wavelength start", self.target_wavelength-self.step_universal)
                fdtd.setnamed("source", "wavelength stop", self.target_wavelength+self.step_universal)
                fdtd.setglobalsource("wavelength start",self.target_wavelength-self.step_universal)
                fdtd.setglobalsource("wavelength stop",self.target_wavelength+self.step_universal)
            else:
                fdtd.setnamed("source", "wavelength start", self.wavelengths[1])
                fdtd.setnamed("source", "wavelength stop", self.wavelengths[2])
                fdtd.setglobalsource("wavelength start",self.wavelengths[1])
                fdtd.setglobalsource("wavelength stop",self.wavelengths[2])
        
        except:
            pass
        # Runs the simularion
        if self.run:
            if not self.local:
                fdtd.save()
                fdtd.close()
                self.launch.simulate(self.filename_FDTD)
                self.launch.get_download(sleep=10)
                fdtd = lumapi.FDTD(filename=self.filename_FDTD)
            else:
                fdtd.run()
            
            # checks if the simulation has diverged and if so it launches a new simulation with stabilized profile. It has a tradeoff of taking more time
            if fdtd.simulationdiverged() == 1 and profile == 1:
                fdtd.close()
                print("Warning: Fields diverging. Retrying with stabilized profile.")
                return Universal_Design.run_simulation_FDTD(self, accuracy=accuracy, universal=universal, bayesian=bayesian, profile=2)
            
            if fdtd.simulationdiverged() == 1 and profile == 2:
                fdtd.close()
                print("Warning: Fields still diverging. Returning 0.")
                if bayesian is False:
                    return 0, 0, 0
                else:
                    return 0, 0, 0, 0
          
        #gets the results and saves the files
            if bayesian is False:
                return self.get_results(fdtd)
            else:
                return self.get_results_bayesian(fdtd)
        else:
            fdtd.save()
            fdtd.close()

    def get_results(self, fdtd):
        
        # receives the data of the analysis group
        purcell_factor = fdtd.getresult("analysis group", "T")
        collection_eff = fdtd.getresult("analysis group", "collection_efficiency_50x_data")
        
        # saves the material name of the substrate
        substrate_material = fdtd.getnamed("substrate", "material")
        
           
        # Extract wavelength data (assuming the first column contains the wavelength)
        wavelengths = purcell_factor["lambda"]  # Extract wavelength in meters
        wavelengths_nm=wavelengths*1e9
        
        # Extract Purcell factor and collection efficiency data
        purcell_values = purcell_factor["Purcell"]  # Extract Purcell factor
        collection_values = collection_eff["Collection Efficiency"]  # Extract collection efficiency
        
        
        # Plot Purcell Factor and Collection Efficiency
        fig, ax1 = plt.subplots(figsize=(8, 5))
    
        # Plot Purcell Factor on the left y-axis
        ax1.plot(wavelengths_nm, purcell_values, label="Purcell Factor", color="blue")
        ax1.set_xlabel("Wavelength (nm)")
        ax1.set_ylabel("Purcell Factor", color="blue")
        ax1.tick_params(axis='y', labelcolor="blue")
        ax1.grid(True)
        
        # Create a second y-axis for Collection Efficiency
        ax2 = ax1.twinx()
        ax2.plot(wavelengths_nm, collection_values, label="Collection Efficiency", color="red")
        ax2.set_ylabel("Collection Efficiency", color="red")
        ax2.tick_params(axis='y', labelcolor="red")
        
        # Title and legend
        plt.title("Purcell Factor & Collection Efficiency vs. Wavelength")
        fig.tight_layout()  # Adjust layout for better fit
        plt.show()
        
        
        # Get the wavelength corresponding to max Purcell factor
        max_index = np.argmax(purcell_values)
        current_wavelength = wavelengths[max_index]
        
        try:
            # gets the real and imaginary part of the refractive index of the cavity and substrate for the current and target wavelength
            real_index_current_cavity=np.real(fdtd.getindex(self.material_name,C/current_wavelength))
            real_index_target_cavity=np.real(fdtd.getindex(self.material_name,C/self.target_wavelength))
            real_index_current_substrate=np.real(fdtd.getindex(substrate_material,C/current_wavelength))
            real_index_target_substrate=np.real(fdtd.getindex(substrate_material,C/self.target_wavelength))
            
        except:
            pass
        
        fdtd.close()
        
        #prints results of the simulation
        print("\n===== Final Simulation Results =====")
        print(f"Final Resonance Wavelength: {current_wavelength[0]*1e9} nm")
        print(f"Maximum Purcell Factor: {purcell_values[max_index]}")
        print(f"Collection Efficiency at Resonance: {collection_values[max_index]}")

        
        return current_wavelength[0], purcell_values[max_index] , collection_values[max_index], [real_index_current_cavity,real_index_current_substrate,real_index_target_cavity,real_index_target_substrate]
  
    def get_results_bayesian(self, fdtd):
        # Track statistics for max-score normalization
        purcell_values = []
        collection_values = []
        
        # Get results safely
        purcell_factor = fdtd.getresult("analysis group", "T")
        collection_eff = fdtd.getresult("analysis group", "collection_efficiency_50x_data")
        
        if purcell_factor is None or collection_eff is None:
            print("Warning: No data retrieved from Lumerical. Returning a bad score.")
            return -1e6  # Return a bad score if there's an issue

        wavelengths = purcell_factor["lambda"].flatten()
        wavelength_diff = np.abs(wavelengths - self.target_wavelength)
        min_diff_index = np.argmin(wavelength_diff)

        if "Purcell" not in purcell_factor or "Collection Efficiency" not in collection_eff:
            print("Warning: Missing expected keys in the result dictionary.")
            return -1e6

        # Extract values at the closest wavelength to 750 nm
        purcell_value = purcell_factor["Purcell"][min_diff_index]
        collection_value = collection_eff["Collection Efficiency"][min_diff_index]

        # Update statistics
        purcell_values.append(purcell_value)
        collection_values.append(collection_value)
        
        # # Check if the new Purcell value exceeds the max and update
        # if purcell_value > self.max_purcell:
        #     self.max_purcell = purcell_value
        #     seen = 1

        # normalized_purcell = purcell_value / self.max_purcell
        # normalized_collection = collection_value / self.max_collection
        
        # Balanced scoring
        score= (-1/purcell_value)**2+(1-collection_value)**2
        # score = -(self.weight_purcell * normalized_purcell + self.weight_collection * normalized_collection)
        self.all_scores.append((score, purcell_value, collection_value))

        return score, purcell_value, collection_value
    
    def Universal_Simulation(self,num_modes,chosen_mode):
        
        # sets geometrical parameters 
        parameters = {
            "height_cavity": self.parameters["height_cavity"],
            "height_substrate": self.parameters["height_substrate"],
            "n_rings": self.parameters["n_rings"],
            "radius_mesa": self.parameters["radius_mesa"],
            "ring_period": self.parameters["ring_period"],
            "duty_cycle": self.parameters["duty_cycle"],
            "material": self.material_name
        }
        
        #updates parameters
        Universal_Design.set_parameters(self, parameters)
        
        #runs the FDE simulation and receives the effective refractive index
        neff_1=Universal_Design.run_simulation_FDE(self,self.target_wavelength,num_modes,chosen_mode)
        
        # Calculate the ring period based on the target wavelength and effective index
        ring_period = self.target_wavelength / neff_1
        radius_mesa=ring_period
        
        #updates parameters
        parameters = {
            "height_cavity": self.parameters["height_cavity"],
            "height_substrate": self.parameters["height_substrate"],
            "n_rings": self.parameters["n_rings"],
            "radius_mesa": radius_mesa,
            "ring_period": ring_period,
            "duty_cycle": self.parameters["duty_cycle"],
            "material": self.material_name
        }
        Universal_Design.set_parameters(self, parameters)
        
        #Calculating alfa
        current_wavelength, _ , _ ,  real_index = Universal_Design.run_simulation_FDTD(self,universal=True)
        alfa=self.target_wavelength/current_wavelength

        #Calculating betas
        beta_1=real_index[0]/real_index[2]
        beta_2=real_index[1]/real_index[3]

        #updating parameters
        height_cavity_updated=self.parameters["height_cavity"]*alfa*beta_1
        height_substrate_updated=self.parameters["height_substrate"]*alfa*beta_2
        
        
        parameters = {
            "height_cavity": height_cavity_updated,
            "height_substrate": height_substrate_updated,
            "n_rings": self.parameters["n_rings"],
            "radius_mesa": radius_mesa,
            "ring_period": ring_period,
            "duty_cycle": self.parameters["duty_cycle"],
            "material": self.material_name
        }
        Universal_Design.set_parameters(self, parameters)
        
        #calculate gama        
        neff_current_gama=Universal_Design.run_simulation_FDE(self,current_wavelength,num_modes,chosen_mode)
        neff_target_gama=Universal_Design.run_simulation_FDE(self,self.target_wavelength,num_modes,chosen_mode)
        gama=neff_current_gama/neff_target_gama
        
        #update parameters
        ring_period_updated=ring_period*alfa*gama
        radius_mesa_updated=ring_period_updated

        #Sets all the optimal parameters
        parameters = {
            "height_cavity": height_cavity_updated[0][0],
            "height_substrate": height_substrate_updated[0][0],
            "n_rings": self.parameters["n_rings"],
            "radius_mesa": radius_mesa_updated[0][0],
            "ring_period": ring_period_updated[0][0],
            "duty_cycle": self.parameters["duty_cycle"],
            "material": self.material_name
        }
        Universal_Design.set_parameters(self, parameters)
        # current_wavelength_updated, purcell_max_value, collection_max_value,  _ =Universal_Design.run_simulation_FDTD(self)
                   
        # print("\n===== Final Simulation Results =====")
        # print(f"Final Resonance Wavelength: {current_wavelength_updated*1e9} nm")
        # print(f"Maximum Purcell Factor: {purcell_max_value}")
        # print(f"Collection Efficiency at Resonance: {collection_max_value}")

        # print("\n=================================\n")  
        
        # prints results of optimization
        print("\n===== Optimization Results =====")
        print(f"α (Scaling Factor): {alfa}")
        print(f"β₁ (Cavity Material Correction): {beta_1[0][0]}")
        print(f"β₂ (Substrate Material Correction): {beta_2[0][0]}")
        print(f"γ (Effective Index Correction): {gama[0][0]}")

        print("\n===== Updated Parameters =====")
        print(f"Updated Cavity Height: {height_cavity_updated[0][0]*1e6} µm")
        print(f"Updated Substrate Height: {height_substrate_updated[0][0]*1e6} µm")
        print(f"Updated Ring Period: {ring_period_updated[0][0]*1e6} µm")
        print(f"Updated Mesa Radius: {radius_mesa_updated[0][0]*1e6} µm")
        print("Duty Cycle:", self.parameters["duty_cycle"])
        print("Number of Rings:", self.parameters["n_rings"])
 
    def Bayesian_Optimization(self, n_iterations):
        
        if n_iterations == 0:
            return None
        
        params_uni_design = self.parameters

        
        # Filter out fixed parameters before defining optimization space
        param_space = []
        param_names = []
        
        for param, value in params_uni_design.items():
            if param in self.fixed_parameters:
                continue  # Skip fixed parameters, they shouldn't be optimized
            
        
            if not isinstance(value, (int, float)):  # Skip non-numeric parameters
                continue
            
            if self.holes is False:
                if param=="hole_diameter" or param=="spacing":
                    continue
        
            if param == "n_rings":
                param_space.append(Integer(value - self.change_in_ring, value + self.change_in_ring, name=param))
            elif param == "ring_period" or param == "radius_mesa" or param=="duty_cycle": #or param == "hole_diameter" or param == "spacing":
                param_space.append(Real(value * (1 - 0.1), value * (1 + 0.1), name=param))
            else:
                param_space.append(Real(value * (1 - self.change_in_param), value * (1 + self.change_in_param), name=param))
        
            param_names.append(param)  # Keep track of optimized parameter names
        
        # Initialize Bayesian Optimizer
        optimizer = Optimizer(dimensions=param_space, acq_func="gp_hedge", n_initial_points=5, random_state=42)
        
        all_parameter_suggestions = []  # To keep track of all suggested parameters
        
        for i in range(n_iterations):
            suggested_params = optimizer.ask()
            all_parameter_suggestions.append(suggested_params)  # Store the suggested parameters
        
            # Ensure valid number of rings
            if "n_rings" in param_names:
                ring_index = param_names.index("n_rings")
                if suggested_params[ring_index] < 1:
                    suggested_params[ring_index] = params_uni_design["n_rings"]
        
            # Create parameter dictionary, merging optimized and fixed parameters
            parameters = {param: value for param, value in zip(param_names, suggested_params)}
            parameters.update(self.fixed_parameters)  # Ensure fixed parameters are used
        
            Universal_Design.set_parameters(self, parameters)
        
            score, purcell, collection = Universal_Design.run_simulation_FDTD(self, bayesian=True)
            optimizer.tell(suggested_params, score)
            
            # if seen == 0:
            #     optimizer.tell(suggested_params, score)
            # else:
            #     # Reset optimizer after max_purcell is updated
            #     updated_scores = []
            #     for s, p, c in self.all_scores:
            #         normalized_purcell = p / self.max_purcell
            #         normalized_collection = c / self.max_collection
            #         # Balanced scoring
            #         score = -(self.weight_purcell * normalized_purcell + self.weight_collection * normalized_collection)
            #         updated_scores.append((score, p, c))
                 
            #     self.all_scores=updated_scores    
            #     # Reinitialize optimizer with updated parameter space
            #     optimizer = Optimizer(dimensions=param_space, acq_func="gp_hedge", n_initial_points=5, random_state=42)
                
            #     # Tell the optimizer about the new scores with their respective parameters
            #     for idx, (score, p, c) in enumerate(updated_scores):
            #         optimizer.tell(all_parameter_suggestions[idx], score)  # Map score to corresponding parameters
                
                
            show_score=1/score  
            # Print iteration details
            log_entry = (
                f"Iteration {i+1}/{n_iterations}: "
                f"Params = {parameters}, "
                f"Purcell Factor = {purcell:.6f}, "
                f"Collection Efficiency = {collection:.6f}, "
                f"Score = {show_score:.2f}\n"
            )
            print(log_entry, end="")
        
        # Get best parameters
        best_index = np.argmin([s[0] for s in self.all_scores])
        
        best_params = optimizer.Xi[best_index]
        best_score, best_purcell, best_collection = self.all_scores[best_index]
        
        # Merge best parameters with fixed ones
        final_parameters = {param: value for param, value in zip(param_names, best_params)}
        final_parameters.update(self.fixed_parameters)  # Overwrite with fixed values
        
        # Print final best parameters including fixed ones
        print("\nBest Parameters Found (including fixed ones):")
        for param, value in final_parameters.items():
            if param=="n_rings":
                print(f"{param}: {value:.0f}")
            
            elif param=="duty_cycle":
                print(f"{param}: {value:.3f}")
            else:
                print(f"{param}: {value*10e8:.3f}nm")
        show_best_score=1/best_score
        print(f"Best Score: {show_best_score:.6f}")
        print(f"Best Purcell Factor: {best_purcell:.6f}")
        print(f"Best Collection Efficiency: {best_collection:.6f}")
        
        # Ensure final best parameters are set correctly
        Universal_Design.set_parameters(self, final_parameters)


class LumericalFDTDSetup:
    def __init__(self, folder,material_name,layer_name,materials_file, target_wv, layer, holes, angle):
        """
        Initializes the Lumerical FDTD setup with the specified cavity material.
        """
        
        cavity_file=[materials_file[0],materials_file[1]]
        layer_file=[materials_file[2],materials_file[3]]
        self.parameters = {
            "duty_cycle": 0.7,
            "r_ring": 300e-9,
            "alfa": 1.0,
            "r_circle": 500e-9,
            "height": 220e-9,
            "n_rings": 5,
            "material": "cavity_material",
            "height_substrate": 250e-9,
            "hole_diameter": 135e-9,
            "spacing": 210e-9 
        }
        self.fdtd = lumapi.FDTD()  # Connect to Lumerical FDTD
        self.fde= lumapi.MODE() # Connect to Lumerical FDE
        
        self.angle=angle
        self.want_layer=layer
        self.holes=holes
        self.target_wv=target_wv
        self.anisotropic=None
        self.cavity_name=material_name
        self.layer_name=layer_name
        self.cavity_material = self.create_material_file(folder,material_name,cavity_file)
        self.layer_material = self.create_material_file(folder,layer_name,layer_file)
        
        
    def setup_simulation_fdtd(self,folder,file):
        """
        Sets up the entire simulation in Lumerical FDTD.
        """
        solver="FDTD"
        self._add_material(solver,self.cavity_material,self.cavity_name)
        self._add_material(solver,self.layer_material,self.layer_name)
        self.fdtd.setmaterial(self.layer_name, "color", np.array([0, 0, 1, 1]))
        self._setup_cavity(solver)
        if self.want_layer is True:
            self._setup_layer(solver)
        self._setup_substrate(solver)
        self._setup_analysis(solver)
        if self.want_layer is True:
            self._setup_mesh(solver)
        self.save_simulation(folder,file,solver)
        print("Lumerical FDTD setup completed successfully!")
    
    def setup_simulation_fde(self,folder,file):
        """
        Sets up the entire simulation in Lumerical FDTD.
        """
        solver="FDE"
        self._add_material(solver,self.cavity_material,self.cavity_name)
        self._add_material(solver,self.layer_material,self.layer_name)
        self.fde.setmaterial(self.layer_name, "color", np.array([0, 0, 1, 1]))
        self._setup_cavity(solver)
        if self.want_layer is True:
            self._setup_layer(solver)
        self._setup_substrate(solver)
        self.fde.addfde()
        if self.want_layer is True:
            self._setup_mesh(solver)
        self.save_simulation(folder,file,solver)
        print("Lumerical FDE setup completed successfully!")

    
    def _add_material(self,solver,filename,my_material):
        if solver=="FDTD":
            solver=self.fdtd
        elif solver=="FDE":
            solver=self.fde
        else:
            raise ValueError("Expected 'FDTD' or 'FDE'")

        # Extract the file name without the extension
        self.parameters["material"]=my_material
        
        if self.anisotropic is False:
            # Define the Lumerical script
            script = self._get_lum_script_material_not_anisotropic(filename,my_material)
            solver.eval(script)
            
            real_index_target=np.real(solver.getindex(self.parameters["material"],C/self.target_wv))
            imag_index_target=np.imag(solver.getindex(self.parameters["material"],C/self.target_wv))
            
            script_2= self._get_lum_script_not_dispersive(real_index_target,imag_index_target)
            solver.eval(script_2)
            
        else:
            # Define the Lumerical script
            script = self._get_lum_script_material_anisotropic(filename,my_material)
            solver.eval(script)
            
            real_index_target_x=np.real(solver.getindex(self.parameters["material"],C/self.target_wv,1))
            imag_index_target_x=np.imag(solver.getindex(self.parameters["material"],C/self.target_wv,1))
            real_index_target_y=np.real(solver.getindex(self.parameters["material"],C/self.target_wv,2))
            imag_index_target_y=np.imag(solver.getindex(self.parameters["material"],C/self.target_wv,2))
            real_index_target_z=np.real(solver.getindex(self.parameters["material"],C/self.target_wv,3))
            imag_index_target_z=np.imag(solver.getindex(self.parameters["material"],C/self.target_wv,3))
            
            script_2= self._get_lum_script_not_dispersive_ani(real_index_target_x,imag_index_target_x,real_index_target_y,imag_index_target_y,real_index_target_z,imag_index_target_z)
            solver.eval(script_2)
        
    def _setup_cavity(self,solver):
        
        if solver=="FDTD":
            solver=self.fdtd
        elif solver=="FDE":
            solver=self.fde
        else:
            raise ValueError("Expected 'FDTD' or 'FDE'")
        
        """
        Sets up the cavity structure in Lumerical FDTD.
        """
        solver.addstructuregroup()
        solver.set("name", "cavity")  # Name the structure group
        
        if self.holes is False:
            # Execute the script in Lumerical via Python API
            solver.adduserprop("duty_cycle",0, self.parameters["duty_cycle"])
            solver.adduserprop("r_ring",2, self.parameters["r_ring"])
            solver.adduserprop("alfa",0, self.parameters["alfa"])
            solver.adduserprop("r_circle",2, self.parameters["r_circle"])
            solver.adduserprop("height",2, self.parameters["height"])
            solver.adduserprop("n_rings",0, self.parameters["n_rings"])
            solver.adduserprop("material",1, self.parameters["material"])
            solver.adduserprop("theta start",0, 0)
            solver.adduserprop("theta stop",0, 360)
            solver.adduserprop("resolution",0, 100)
            solver.adduserprop("angle_trench",0, self.angle)
            
        
            # Define cavity structure script
            solver.set("script", self._get_lum_script_cavity())
        
        else:
            solver.adduserprop("ring_period",2, self.parameters["r_ring"])
            solver.adduserprop("radius_mesa",2, self.parameters["r_circle"])
            solver.adduserprop("height",2, self.parameters["height"])
            solver.adduserprop("n_rings",0, self.parameters["n_rings"])
            solver.adduserprop("material",1, self.parameters["material"])
            solver.adduserprop("hole_diameter",2, self.parameters["hole_diameter"])
            solver.adduserprop("spacing",2, self.parameters["spacing"])
            
            # Define cavity structure script
            solver.set("script", self._get_lum_script_cavity_holes())
        
    
    def _setup_layer(self,solver):
        if solver=="FDTD":
            solver=self.fdtd
        elif solver=="FDE":
            solver=self.fde
        else:
            raise ValueError("Expected 'FDTD' or 'FDE'")
        
        """
        Sets up the cavity structure in Lumerical FDTD.
        """
        solver.addstructuregroup()
        solver.set("name", "layer")  # Name the structure group
    
        # Execute the script in Lumerical via Python API
        # solver.set("z", 0.2e-6)
        solver.adduserprop("duty_cycle",0, self.parameters["duty_cycle"])
        solver.adduserprop("r_ring",2, self.parameters["r_ring"])
        solver.adduserprop("alfa",0, self.parameters["alfa"])
        solver.adduserprop("r_circle",2, self.parameters["r_circle"])
        solver.adduserprop("height",2, 0.002e-6)
        solver.adduserprop("n_rings",0, self.parameters["n_rings"])
        solver.adduserprop("material",1, self.layer_name)
        
        # Define layer structure script
        solver.set("script", self._get_lum_script_cavity())
        
    def _setup_mesh(self,solver):
        if solver=="FDTD":
            solver=self.fdtd
        elif solver=="FDE":
            solver=self.fde
        else:
            raise ValueError("Expected 'FDTD' or 'FDE'")
        
        """
        Sets up the overide mesh around the layer.
        """
        solver.addmesh()
        # enable in Z direction and disable in X,Y directions
        solver.set("override x mesh",0)
        solver.set("override y mesh",0)
        solver.set("override z mesh",1)
        solver.set("set maximum mesh step",1)
        solver.set("dz",0.5e-9)
        solver.set("based on a structure",1)
        solver.set("structure", "layer")
        
        
    
    def _setup_substrate(self,solver):
        
        if solver=="FDTD":
            solver=self.fdtd
        elif solver=="FDE":
            solver=self.fde
        else:
            raise ValueError("Expected 'FDTD' or 'FDE'")
        
        """
        Sets up the substrate structure group.
        """
        solver.addstructuregroup()
        solver.set("name", "substrate")
        
        # Add substrate parameters
        solver.adduserprop("big_radius", 2, 30e-6)
        solver.adduserprop("h_sio2", 2, self.parameters["height_substrate"])
        solver.adduserprop("h_au", 2, 0.15e-6)
        solver.adduserprop("h_si", 2, 30e-6)
        solver.adduserprop("alfa", 0, 1)
        solver.adduserprop("material", 1, "SiO2 (Glass) - Palik")
        
        # Define substrate structure
        solver.set("script", self._get_lum_script_substrate())
    
    def _setup_analysis(self,solver):
        
        if solver=="FDTD":
            solver=self.fdtd
        elif solver=="FDE":
            solver=self.fde
        else:
            raise ValueError("Expected 'FDTD' or 'FDE'")
        
        """
        Sets up the analysis and simulation components.
        """
        number_frequency_points=50
        
        solver.adddipole()
        solver.set("theta", 90)
        solver.addfdtd()
        solver.addanalysisgroup()
        
        # Add analysis parameters
        solver.adduserprop("x span", 2, 0.3e-6)
        solver.adduserprop("y span", 2, 0.3e-6)
        solver.adduserprop("z span", 2, 0.3e-6)
        solver.adduserprop("z_profile", 2, 0.45e-6)
        solver.adduserprop("x_span_prof", 2, 5e-6)
        solver.adduserprop("y_span_prof", 2, 5e-6)
        solver.addanalysisprop("n_freq", 0, number_frequency_points)
        solver.addanalysisresult("T")
        solver.addanalysisresult("collection_efficiency_20x_data")
        solver.addanalysisresult("collection_efficiency_50x_data")
        
        # Set up analysis scripts
        solver.set("setup script", self._get_lum_script_analysis_setup())
        solver.set("analysis script", self._get_lum_script_analysis())
        solver.setglobalmonitor("frequency points",number_frequency_points);
           
    def _get_lum_script_not_dispersive_ani(self,real_x,imag_x,real_y,imag_y,real_z,imag_z):
        return f"""
        # Define constants
        C = 299792458;  # Speed of light in m/s
        matName = "Not Dispersive {self.parameters["material"]}";  # Material name

        real_nb=[{real_x},{real_y},{real_z}];
        imag_nb=[{imag_x},{imag_y},{imag_z}];
        
        # Create the sampled data material in Lumerical
        temp = addmaterial("(n,k) Material");
        setmaterial(temp, "name", matName);  # Rename material
        setmaterial(matName, "anisotropy", 1);
        setmaterial(matName, {{"Refractive Index": real_nb, "Imaginary Refractive Index": imag_nb }});

        # Print success message
        ?"Not Dispersive material created successfully!";

        """      
        
    def _get_lum_script_not_dispersive(self,real,imag):
        return f"""
        # Define constants
        C = 299792458;  # Speed of light in m/s
        matName = "Not Dispersive {self.parameters["material"]}";  # Material name


        # Create the sampled data material in Lumerical
        temp = addmaterial("(n,k) Material");
        setmaterial(temp, "name", matName);  # Rename material
        setmaterial(matName, "anisotropy", 0);
        setmaterial(matName, {{"Refractive Index": {real}, "Imaginary Refractive Index": {imag} }});

        # Print success message
        ?"Not Dispersive material created successfully!";

        """  
        
    def _get_lum_script_material_not_anisotropic(self,filename,my_material):
        return f"""
        # Define constants
        C = 299792458;  # Speed of light in m/s
        matName = "{my_material}";  # Material name

        # Load the TXT file
        filename = "{filename}";  
        data = readdata(filename);

        # Extract data columns
        wl = data(:,1) * 1e-6;  # Convert wavelength from micrometers to meters
        ?wl;
        nx_real = data(:,2);      # Real part of refractive index (n1)
        ?nx_real;
        nx_imag = data(:,3);      # Imaginary part of refractive index (k1)
        

        # Convert wavelength to frequency
        freqs = C / wl;
        
        # Compute complex permittivity: eps = (n + i*k)^2
        epsx = (nx_real + 1i * nx_imag)^2;

        # Create the sampled data matrix (2 columns: frequency | permittivity)
        sampledData = matrix(length(freqs), 2);
        sampledData(:,1) = freqs;  # First column: frequency
        sampledData(:,2) = epsx;    # Second column: complex permittivity

        # Create the sampled data material in Lumerical
        temp = addmaterial("Sampled data");
        setmaterial(temp, "name", matName);  # Rename material
        setmaterial(matName, "max coefficients", 6);  # Set the number of coefficients
        setmaterial(matName,"tolerance", 0);
        setmaterial(matName, "sampled data", sampledData);  # Load the sampled data matrix

        # Print success message
        ?"Sampled data material created successfully!";

        """  
        
    def _get_lum_script_material_anisotropic(self,filename,my_material):
        return f"""
        # Define constants
        C = 299792458;  # Speed of light in m/s
        matName = "{my_material}";  # Material name

        # Load the CSV file
        filename = "{filename}";  
        data = readdata(filename);

        # Extract data columns
        wl = data(:,1) * 1e-6;  # Convert wavelength from micrometers to meters
        nx_real = data(:,2);      # Real part of refractive index (n1)
        nx_imag = data(:,3);      # Imaginary part of refractive index (k1)
        ny_real = data(:,4);      # Real part of refractive index (n1)
        ny_imag = data(:,5);      # Imaginary part of refractive index (k1)
        nz_real = data(:,6);      # Real part of refractive index (n1)
        nz_imag = data(:,7);      # Imaginary part of refractive index (k1)

        # Convert wavelength to frequency
        freqs = C / wl;

        # Compute complex permittivity: eps = (n + i*k)^2
        epsx = (nx_real + 1i * nx_imag)^2;
        epsy = (ny_real + 1i * ny_imag)^2;
        epsz = (nz_real + 1i * nz_imag)^2;

        # Create the sampled data matrix (2 columns: frequency | permittivity)
        sampledData = matrix(length(freqs), 4);
        sampledData(:,1) = freqs;  # First column: frequency
        sampledData(:,2) = epsx;    # Second column: complex permittivity
        sampledData(:,3) = epsy;
        sampledData(:,4) = epsz;

        # Create the sampled data material in Lumerical
        temp = addmaterial("Sampled data");
        setmaterial(temp, "name", matName);  # Rename material
        setmaterial(matName, "max coefficients", 6);  # Set the number of coefficients
        setmaterial(matName,"tolerance", 0);
        setmaterial(matName, "sampled data", sampledData);  # Load the sampled data matrix

        # Print success message
        ?"Sampled data material created successfully!";

        """
    
    def _get_lum_script_cavity(self):
        """Returns the Lumerical script for the cavity setup."""
        return """

# Lumerical script to create cavity
        
deleteall;
w_ring=duty_cycle*r_ring;
w_ring=w_ring*alfa;
r_ring=r_ring*alfa;
r_circle=r_circle*alfa;
height=height*alfa;
addcircle;
set("radius",r_circle);
set("z min",0);
set("z max",height);
set("material",material);

# generate pointing outwards toroid

radius=r_circle;
# simplify variable names by removing spaces
theta_start = %theta start%;
theta_stop = %theta stop%;

# USER specifies polygon vertices here. The 3D structure will be created by revolving this shape around Z axis, with a radius R.
# Note: It is OK, but not necessary to close the polygon
V=matrix(3,2);
V(1,1:2) = [0, height];
V(2,1:2) = [0,  0];
V(3,1:2) = [height/tan(angle_trench*pi/180), 0];

# plot(pinch(V,2,1)*1e6,pinch(V,2,2)*1e6,"x (um)","y (um)","Polygon outline");   # plot vertices (for debugging)


# calculate slice thickness
th = 4*pi*radius/resolution;  # divide circumference by resolution
th = th * 1.1;       # scale up thickess slighly. Required when polygon vertices extend beyond zero, which increases the maximum radius.

# if partial revolution, use only a fraction of slices
resolution=round(resolution*abs(theta_start-theta_stop)/360); 

# Calculate revolution angle vector
theta = linspace(theta_start*pi/180,theta_stop*pi/180,resolution);

for(i=1:resolution) {
  addpoly;
  set("vertices",V);
  set("first axis","x");
  set("rotation 1",90);
  set("second axis","z");
  set("rotation 2",theta(i)*180/pi);
  set("x",radius*cos(theta(i)));
  set("y",radius*sin(theta(i)));

  set("z min",-th/2);
  set("z max",th/2);
  set("material",material);
}



        
# Add rings
for(j=1:n_rings) {
	inner=r_circle+j*r_ring-w_ring;
	outer=r_circle+j*r_ring;
	addring;
        set("x",0);
	set("y",0);
	set("inner radius",inner);
	set("outer radius",outer);
	set("z min", 0);
	set("z max",height);    
	set("material",material);

# generate pointing inwards toroid

radius=inner;
# simplify variable names by removing spaces
theta_start = %theta start%;
theta_stop = %theta stop%;

# USER specifies polygon vertices here. The 3D structure will be created by revolving this shape around Z axis, with a radius R.
# Note: It is OK, but not necessary to close the polygon
V=matrix(3,2);
V(1,1:2) = [0, height];
V(2,1:2) = [0,  0];
V(3,1:2) = [-height/tan(angle_trench*pi/180), 0];


# plot(pinch(V,2,1)*1e6,pinch(V,2,2)*1e6,"x (um)","y (um)","Polygon outline");   # plot vertices (for debugging)


# calculate slice thickness
th = 4*pi*radius/resolution;  # divide circumference by resolution
th = th * 1.1;       # scale up thickess slighly. Required when polygon vertices extend beyond zero, which increases the maximum radius.

# if partial revolution, use only a fraction of slices
resolution=round(resolution*abs(theta_start-theta_stop)/360); 

# Calculate revolution angle vector
theta = linspace(theta_start*pi/180,theta_stop*pi/180,resolution);

for(i=1:resolution) {
  addpoly;
  set("vertices",V);
  set("first axis","x");
  set("rotation 1",90);
  set("second axis","z");
  set("rotation 2",theta(i)*180/pi);
  set("x",radius*cos(theta(i)));
  set("y",radius*sin(theta(i)));

  set("z min",-th/2);
  set("z max",th/2);
  set("material",material);

}

# generate pointing outwards toroid
if (j!=n_rings){
radius=outer;
# simplify variable names by removing spaces
theta_start = %theta start%;
theta_stop = %theta stop%;

# USER specifies polygon vertices here. The 3D structure will be created by revolving this shape around Z axis, with a radius R.
# Note: It is OK, but not necessary to close the polygon
V=matrix(3,2);
V(1,1:2) = [0, height];
V(2,1:2) = [0,  0];
V(3,1:2) = [height/tan(angle_trench*pi/180), 0];

# plot(pinch(V,2,1)*1e6,pinch(V,2,2)*1e6,"x (um)","y (um)","Polygon outline");   # plot vertices (for debugging)


# calculate slice thickness
th = 4*pi*radius/resolution;  # divide circumference by resolution
th = th * 1.1;       # scale up thickess slighly. Required when polygon vertices extend beyond zero, which increases the maximum radius.

# if partial revolution, use only a fraction of slices
resolution=round(resolution*abs(theta_start-theta_stop)/360); 

# Calculate revolution angle vector
theta = linspace(theta_start*pi/180,theta_stop*pi/180,resolution);

for(i=1:resolution) {
  addpoly;
  set("vertices",V);
  set("first axis","x");
  set("rotation 1",90);
  set("second axis","z");
  set("rotation 2",theta(i)*180/pi);
  set("x",radius*cos(theta(i)));
  set("y",radius*sin(theta(i)));

  set("z min",-th/2);
  set("z max",th/2);
  set("material",material);
  
}

}

        }



        """
# finish_radius=r_circle+i=n_rings*r_ring;
# 	# add background Ring
# 	addring;
# 	set("name","background");
#         set("x",0);
#         set("y",0);
#         set("inner radius",finish_radius);
#         set("outer radius",finish_radius+3e-6);
#         set("z min", 0);
#         set("z max",height);    
#         set("material",material);


        
    def _get_lum_script_cavity_holes(self):
        """Returns the Lumerical script for the cavity setup."""
        return """
        deleteall;
        # Parameters
        hole_diameter = hole_diameter;       # 135 nm hole diameter
        hole_radius = hole_diameter/2;
        spacing = spacing;             # 210 nm spacing between holes
        thickness = height;          # thickness of the hBN layer
        
        # Ring settings
        r_start = radius_mesa;             # starting radius (0.5 micron)             
        r_step = ring_period; 		# step between rings (0.5 micron)
        r_end = n_rings*r_step;               # ending radius (2.0 micron)
        
        radius_hBN = r_end + r_step;
        
        # Create the main hBN disk
        addcircle;
        set("name", "hBN_disk");
        set("material", material);       # Make sure you have an hBN material defined
        set("x", 0);
        set("y", 0);
        set("z", 0);
        set("radius", radius_hBN);
        set("z min", 0);
        set("z max", thickness);
        
        # Loop over rings
        ring_index = 1;
        for (r = r_start:r_step:r_end) {
            
            circumference = 2*pi*r;
            n_holes = round(circumference/spacing);
            
            ?("Ring " + num2str(ring_index) + " at r = " + num2str(r/1e-6) + " um, " + num2str(n_holes) + " holes");
        
            # Add holes on this ring
            for (i = 1:n_holes) {
                langle = 2*pi*(i-1)/n_holes;
                x = r*cos(langle);
                y = r*sin(langle);
                
                addcircle;
                set("name", "hole_r" + num2str(ring_index) + "_" + num2str(i));
                # set("material", "<Object defined dielectric>");
                set("x", x);
                set("y", y);
                set("z", 0);
                set("radius", hole_radius);
                set("z min", 0);
                set("z max", thickness);
            }
            
            ring_index = ring_index + 1;
        }


        """
    def _get_lum_script_substrate(self):
        """Returns the Lumerical script for the substrate setup."""
        return """
        deleteall;
        # Lumerical script to create substrate
        deleteall;

        h_sio2=h_sio2*alfa;
        addcircle;
        set("radius", big_radius);
        set("z min", -h_sio2);
        set("z max",0);
        set("material",material);

        addcircle;
        set("radius", big_radius);
        set("z min", -h_au-h_sio2);
        set("z max",-h_sio2);
        set("material","Au (Gold) - Palik");

        addcircle;
        set("radius", big_radius);
        set("z min", -h_au-h_sio2-h_si);
        set("z max",-h_sio2-h_au);
        set("material","Si (Silicon) - Palik");
        """
    
    def _get_lum_script_analysis_setup(self):
        """Returns the Lumerical script for analysis setup."""
        return """
        deleteall;
        addprofile; set("name","profile");
        ##############################################
        # Transmission box
        # This script creates a box of monitors with a
        # given x,y,z span
        #
        # Input properties
        # x span, y span, z span: size of the box
        #
        # Tags: transmission box power
        #
        # Copyright 2013 Lumerical Solutions Inc
        ##############################################

        # simplify variable names by removing spaces
        x_span = %x span%;
        y_span = %y span%;
        z_span = %z span%;

        # add monitors
        addpower; set("name","x1");
        addpower; set("name","x2");
        addpower; set("name","y1");
        addpower; set("name","y2");
        addpower; set("name","z1");
        addpower; set("name","z2");

        # set monitor orientation
        selectpartial("x"); set("monitor type","2D X-normal");
        selectpartial("y"); set("monitor type","2D Y-normal");
        selectpartial("z"); set("monitor type","2D Z-normal");
        select("profile"); set("monitor type","2D Z-normal");

        # set monitor positions
        select("x1");
        set("x",-x_span/2);
        set("y",0);
        set("z",0);
        set("y span",y_span);
        set("z span",z_span);

        select("x2");
        set("x",x_span/2);
        set("y",0);
        set("z",0);
        set("y span",y_span);
        set("z span",z_span);

        select("y1");
        set("x",0);
        set("y",-y_span/2);
        set("z",0);
        set("x span",x_span);
        set("z span",z_span);

        select("y2");
        set("x",0);
        set("y",y_span/2);
        set("z",0);
        set("x span",x_span);
        set("z span",z_span);

        select("z1");
        set("x",0); 
        set("y",0); 
        set("z",-z_span/2);
        set("x span",x_span); 
        set("y span",y_span);

        select("z2");
        set("x",0);
        set("y",0);
        set("z",z_span/2);
        set("x span",x_span);
        set("y span",y_span);

        select("profile");
        set("x",0);
        set("y",0);
        set("z",z_profile);
        set("x span",x_span_prof);
        set("y span",y_span_prof);
        # disable z monitors in 2D simulations
        selectpartial("z");
        set("simulation type","3D");

        # only record net power transmission, not field components
        selectpartial("1");
        set("output power",1);
        set("output Ex",0);
        set("output Ey",0);
        set("output Ez",0);
        set("output Hx",0);
        set("output Hy",0);
        set("output Hz",0);
        set("output Px",0);
        set("output Py",0);
        set("output Pz",0);
        selectpartial("2");
        set("output power",1);
        set("output Ex",0);
        set("output Ey",0);
        set("output Ez",0);
        set("output Hx",0);
        set("output Hy",0);
        set("output Hz",0);
        set("output Px",0);
        set("output Py",0);
        set("output Pz",0);
        """
    
    def _get_lum_script_analysis(self):
        """Returns the Lumerical script for analysis execution."""
        return """
        ##############################################
        # Transmission box
        # This script calculates the net power out of the
        # box of monitors. This script functions with symmetry
        # boundary conditions, and in both 2D and 3D simulations
        # It also works with period boundaries, when some sides of
        # the box are extended beyond the simulation boundary. 
        #
        # Output properties
        # T: power transmission flowing out of box
        #
        # Tags: transmission box power
        #
        # Copyright 2013 Lumerical Solutions Inc
        ##############################################

        # get frequency vector and simulation dimension from an avaialble monitor
        if (havedata("x2")) { mname="x2";  }
        if (havedata("y2")) { mname="y2";  }
        if (havedata("z2")) { mname="z2";  }
        f=getdata(mname,"f");   
        dim = getdata(mname,"dimension");


        if(havedata("x2")){ Px2 =   transmission("x2"); } else { Px2=0;   }
        if(havedata("x1")){ Px1 =  -transmission("x1"); } else { Px1=Px2; }

        if(havedata("y2")){ Py2 =   transmission("y2"); } else { Py2=0;   }
        if(havedata("y1")){ Py1 =  -transmission("y1"); } else { Py1=Py2; }

        # include z monitors if 3D simulation
        if (dim==3) {
          if(havedata("z2")){ Pz2 =   transmission("z2"); } else { Pz2=0;   }
          if(havedata("z1")){ Pz1 =  -transmission("z1"); } else { Pz1=Pz2; }
        }  else {
          Pz2 = 0; Pz1 = 0;
        }

        net_power = Px1 + Px2 + Py1 + Py2 + Pz1 + Pz2;

        T = matrixdataset("T");
        T.addparameter("lambda",c/f,"f",f);
        T.addattribute("Purcell",net_power);


        #########################################################
        #       Perform the far field projection and image result

        half_angle_50x = 53.13; #in degrees, NA = 0.8
        half_angle_20x = 26.74; #in degrees, NA = 0.45

        # choose the central angle of the cone
        cone_center_theta = 0;
        cone_center_phi = 0;

        temp_cone_50x = 1:n_freq;
        temp_cone_20x = 1:n_freq;
        temp_far = 1:n_freq;
        collection_efficiency_50x = 1:n_freq;
        collection_efficiency_20x = 1:n_freq;
        epsilon_obj_50x = 1:n_freq;
        epsilon_obj_20x = 1:n_freq;
        temp = transmission("profile");
        f=getdata("profile","f");

        for(i=1:n_freq) {
            
            E2 = farfield3d("profile",i); # this returns |E|^2 in the far field
            ux = farfieldux("profile",i);
            uy = farfielduy("profile",i);
            
            temp_cone_50x(i) = farfield3dintegrate(E2,ux,uy,half_angle_50x,cone_center_theta,cone_center_phi);
            temp_cone_20x(i) = farfield3dintegrate(E2,ux,uy,half_angle_20x,cone_center_theta,cone_center_phi);    
            temp_far(i)  = farfield3dintegrate(E2,ux,uy);
            
            collection_efficiency_20x(i) = (temp_cone_20x(i)/temp_far(i)*temp(i))/net_power(i);
            collection_efficiency_50x(i) = (temp_cone_50x(i)/temp_far(i)*temp(i))/net_power(i);
            epsilon_obj_50x(i) = temp_cone_50x(i)/temp_far(i);
            epsilon_obj_20x(i) = temp_cone_20x(i)/temp_far(i);
            
        }

        # Display the half angle
        ?"The half angle is: " + num2str(half_angle_50x) + " degrees" +
        " at (theta,phi)=("+num2str(cone_center_theta)+","+num2str(cone_center_phi)+")";
        ?"The half angle is: " + num2str(half_angle_20x) + " degrees" +
        " at (theta,phi)=("+num2str(cone_center_theta)+","+num2str(cone_center_phi)+")";

        #plot(c/f*1e6,collection_efficiency_50x,collection_efficiency_20x,"Wavelength [um]","Transmission");
        #plot(c/f*1e6,epsilon_obj_50x,epsilon_obj_20x,"Wavelength [um]","Coupling efficiency to objective");
        #plot(c/f*1e6,collection_efficiency_50x,collection_efficiency_20x,"Wavelength [um]","Collection efficiency");
        #?"  The normalized transmission by method 1 is: " + num2str(T*100) + " %";

        collection_efficiency_50x_data = matrixdataset("NA 0.8");
        collection_efficiency_50x_data.addparameter("lambda",c/f,"f",f);
        collection_efficiency_50x_data.addattribute("Collection Efficiency",collection_efficiency_50x);

        collection_efficiency_20x_data = matrixdataset("NA 0.45");
        collection_efficiency_20x_data.addparameter("lambda",c/f,"f",f);
        collection_efficiency_20x_data.addattribute("Collection Efficiency",collection_efficiency_20x);
        """

    def save_simulation(self, folder_path, filename, solver):
        
        if solver=="FDTD":
            solver=self.fdtd
        elif solver=="FDE":
            solver=self.fde
        else:
            raise ValueError("Expected 'FDTD' or 'FDE'")
        
        """
        Saves the current Lumerical FDTD simulation to the specified folder.
        
        Parameters:
            folder_path (str): The directory where the simulation should be saved.
            filename (str): The name of the saved simulation file (default: 'simulation.fsp').
        """
        # Ensure the folder exists
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)  # Create the directory if it doesn't exist
    
        # Full file path
        file_path = os.path.join(folder_path, filename)
    
        # Save the simulation in Lumerical
        solver.save(file_path)
        print(f"Simulation saved to: {file_path}")
        solver.close()
        
     # Function to transform CSV file
    def transform_csv(self,input_file, output_file):
         # Read the CSV file
         with open(input_file, 'r') as file:
             reader = csv.reader(file)
             lines = list(reader)
         
         # Separate the data
         #headers = lines[0]  # Get the headers (wl, n)
         n_data = lines[1:]  # n data starts from the second row
         
         # Assuming k data starts immediately after n data ends
         # Find the index where k starts
         k_start_index = len(n_data) // 2  # This assumes n and k data are of equal length
         n_values = n_data[:k_start_index]
         k_values = n_data[k_start_index+1:]
    
         # Merge n and k data
         merged_data = []
         for n_row, k_row in zip(n_values, k_values):
             wl = n_row[0]  # Wavelength is the same for n and k
             n_value = n_row[1]
             k_value = k_row[1]
             merged_data.append([wl, n_value, k_value])
         
         # Write the transformed CSV file
         with open(output_file, 'w', newline='') as file:
             writer = csv.writer(file)
             writer.writerow(['wl', 'n', 'k'])  # Write new header
             writer.writerows(merged_data)     # Write merged data   
                 
     # Function to merge CSV files
    def merge_csv(self,file1, file2, output_file):
         # Read the CSV files
         df1 = pd.read_csv(file1)
         df2 = pd.read_csv(file2)
         
         # Rename columns in df1 and df2 to avoid overlap and to match the naming scheme
         df1 = df1.rename(columns={"n": "n1", "k": "k1"})
         df2 = df2.rename(columns={"n": "n2", "k": "k2"})
         
         # Merge the dataframes on 'wl' column
         merged_df = pd.merge(df1, df2, on='wl', how='outer')
         
         # Copy specific columns from df1 for n1_copy and k1_copy
         merged_df["n1_copy"] = df1.set_index("wl")["n1"].reindex(merged_df["wl"]).values
         merged_df["k1_copy"] = df1.set_index("wl")["k1"].reindex(merged_df["wl"]).values
         
         # Add k2 column with zeros if it does not exist
         if "k2" not in merged_df.columns:
             merged_df["k2"] = 0
         
         # Reorder columns
         column_order = ["wl", "n1", "k1", "n1_copy", "k1_copy", "n2", "k2"]
         merged_df = merged_df[column_order]
         
         # Save the merged dataframe to a new CSV file
         merged_df.to_csv(output_file, index=False)
    
    
    def create_material_file(self,folder,name,files):
         
         file1=files[0]
         file2=files[1]
         
         # Case 1: If only one of the files is None
         if file1 is not None and file2 is None:
             output_file1 = f"{folder}\{name}.txt"
             # Run transform_csv on file1 and return the output
             self.transform_csv(file1, output_file1)
             self.anisotropic=False
             return output_file1
         
         if file2 is not None and file1 is None:
             output_file2 = f"{folder}\{name}.txt"
             # Run transform_csv on file2 and return the output
             self.transform_csv(file2, output_file2)
             self.anisotropic=False
             return output_file2
     
         # Case 2: If both files are provided
         if file1 is not None and file2 is not None:
             output_file1 = f"{folder}\{name}_o.txt"
             output_file2 = f"{folder}\{name}_e.txt"
             # Run transform_csv on both files
             self.transform_csv(file1, output_file1)
             self.transform_csv(file2, output_file2)
             
             # Run merge_csv on the two transformed files and return the output
             final_output_file = f"{folder}\{name}.txt"
             self.merge_csv(output_file1, output_file2, final_output_file)
             self.anisotropic=True
             
             return final_output_file
         
         if file1 is None and file2 is None:
             raise ValueError("Insert the material file")
            
  
