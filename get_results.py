# -*- coding: utf-8 -*-
"""
Created on Thu May 15 14:30:42 2025

@author: kikos
"""
import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
#default path for current release 
sys.path.append(r"D:\Master thesis files\Lumerical\api\python") 
sys.path.append(os.path.dirname(__file__)) #Current directory
import lumapi

def get_results(folder_path,file):
    
    filename_FDTD = os.path.join(folder_path, file)
    fdtd=lumapi.FDTD(filename=filename_FDTD)
    # receives the data of the analysis group
    purcell_factor = fdtd.getresult("analysis group", "T")
    collection_eff = fdtd.getresult("analysis group", "collection_efficiency_50x_data")
    
       
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
    plt.title(f"Purcell Factor & Collection Efficiency vs. Wavelength")
    fig.tight_layout()  # Adjust layout for better fit
    plt.show()
    

    max_index = np.argmax(purcell_values)
    current_wavelength = wavelengths[max_index]

    
    # prints results of the simulation
    print(f"\n===== Final Simulation Results |  {Path(file).stem} =====")
    print(f"Final Resonance Wavelength: {current_wavelength[0]*1e9} nm")
    print(f"Maximum Purcell Factor: {purcell_values[max_index]}")
    print(f"Collection Efficiency at Resonance: {collection_values[max_index]}\n")
    print("Parameters:\n")
    print("Height:",str(round(fdtd.getnamed("cavity","height")*1e9,2))+"nm")
    print("Height Substrate:",str(round(fdtd.getnamed("substrate","h_sio2")*1e9,2))+"nm")
    print("Radius Mesa:",str(round(fdtd.getnamed("cavity","r_circle")*1e9,2))+"nm")
    print("Radius Ring:",str(round(fdtd.getnamed("cavity","r_ring")*1e9,2))+"nm")
    print("Duty Cycle:",round(fdtd.getnamed("cavity","duty_cycle"),2))
    print("Number of Rings:",int(round(fdtd.getnamed("cavity","n_rings"),0)))

    fdtd.close()


# Set the directory path
folder_path = Path(r"D:\Master thesis files\Simulations\Data\Gold\hBN_thin" )

# Get all .fsp files
fsp_files = list(folder_path.glob("*.fsp"))
# fsp_files=["last of the last_800nm_20250609_151019.fsp"]

# "D:\Master thesis files\Simulations\Data\Gold\Dummy_reflectivity\last of the last_800nm_20250609_151019.fsp"

# Process each .fsp file
for file in fsp_files:

    get_results(folder_path,file)


    