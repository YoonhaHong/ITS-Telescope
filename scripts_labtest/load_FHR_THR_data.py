"""
Written by Meike
    read FHR/THR measurements and configs, both from the same results folder
    do that for all results folder associated with one region
    plot FHR/THR vs VCASB for that region
    do that for all regions

Added csv converting part
"""

import json5
import json
import subprocess
import sys
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

base_path = "/home/hipex/MOSS_TEST_RESULTS/babyMOSS-2_4_W21D4"
debug = False
plot = True
csv = True # save the result as csv file

region_collection_FHR = {
    'tb_reg0': {
        "collection_folder": "ScanCollection_20250308_193942",
        "VCASB": [],   # lists for saving the VCASB values from the read files
        "results": [],  # FHR / THR will be saved here
        "color": "salmon"
    },
    'tb_reg1': {
        "collection_folder": "ScanCollection_20250308_194558",
        "VCASB": [],
        "results": [],
        "color": "darkgreen"
    },
    'tb_reg2': {
        "collection_folder": "ScanCollection_20250308_195214",
        "VCASB": [],
        "results": [],
        "color": "dimgrey"
    },
    'tb_reg3': {
        "collection_folder": "ScanCollection_20250308_195829",
        "VCASB": [],
        "results": [],
        "color": "mediumblue"
    },
    'bb_reg0': {
        "collection_folder": "ScanCollection_20250308_191437",
        "VCASB": [],
        "results": [],
        "color": "orangered"
    },
    'bb_reg1': {
        "collection_folder": "ScanCollection_20250308_192055",
        "VCASB": [],
        "results": [],
        "color": "darkturquoise"
    },
    'bb_reg2': {
        "collection_folder": "ScanCollection_20250308_192711",
        "VCASB": [],
        "results": [],
        "color": "yellowgreen"
    },
    'bb_reg3': {
        "collection_folder": "ScanCollection_20250308_193326",
        "VCASB": [],
        "results": [],
        "color": "mediumvioletred"
    }
}

region_collection_THR = {
    'tb_reg0': {
        "collection_folder": "ScanCollection_20250309_032252",
        "VCASB": [],
        "results": [],
        "color": "salmon"
    },
    'tb_reg1': {
        "collection_folder": "ScanCollection_20250309_051416",  
        "VCASB": [],
        "results": [],
        "color": "darkgreen"
    },
    'tb_reg2': {
        "collection_folder": "ScanCollection_20250309_032252",
        "VCASB": [],
        "results": [],
        "color": "dimgrey"
    },
    'tb_reg3': {
        "collection_folder": "ScanCollection_20250309_051416",
        "VCASB": [],
        "results": [],
        "color": "mediumblue"
    },
    'bb_reg0': {
        "collection_folder": "ScanCollection_20250309_032252",
        "VCASB": [],
        "results": [],
        "color": "orangered"
    },
    'bb_reg1': {
        "collection_folder": "ScanCollection_20250309_051416",
        "VCASB": [],
        "results": [],
        "color": "darkturquoise"
    },
    'bb_reg2': {
        "collection_folder": "ScanCollection_20250309_032252",
        "VCASB": [],
        "results": [],
        "color": "yellowgreen"
    },
    'bb_reg3': {
        "collection_folder": "ScanCollection_20250309_051416",
        "VCASB": [],
        "results": [],
        "color": "mediumvioletred"
    }
}



def read_files(config_fileName, results_fileName, measNameForJSON, debug):

    with open(config_fileName) as config_json:

        config_data = json.load(config_json)
        #print(json_data.keys())
        tb_VCASB = config_data['moss_dac_settings']['tb']['VCASB']
        bb_VCASB = config_data['moss_dac_settings']['bb']['VCASB']
        if(debug): print(f"tb VCASB: {tb_VCASB}")
        if(debug): print(f"bb VCASB: {bb_VCASB}")
            
    with open(results_fileName) as results_json:

        results_data = json5.load(results_json)
        tb_results = results_data['tb'][measNameForJSON]
        bb_results = results_data['bb'][measNameForJSON]
        if(debug): print(f"tb {measNameForJSON}: {tb_results}")
        if(debug): print(f"bb {measNameForJSON}: {bb_results}")
        
    # append
    if(region == 'tb_reg0'):
        folder_collection[region]["VCASB"].append(tb_VCASB[0])
        folder_collection[region]["results"].append(tb_results[0])
    elif(region == 'tb_reg1'):
        folder_collection[region]["VCASB"].append(tb_VCASB[1])
        folder_collection[region]["results"].append(tb_results[1])
    elif(region == 'tb_reg2'):
        folder_collection[region]["VCASB"].append(tb_VCASB[2])
        folder_collection[region]["results"].append(tb_results[2])
    elif(region == 'tb_reg3'):
        folder_collection[region]["VCASB"].append(tb_VCASB[3])
        folder_collection[region]["results"].append(tb_results[3])
    elif(region == 'bb_reg0'):
        folder_collection[region]["VCASB"].append(bb_VCASB[0])
        folder_collection[region]["results"].append(bb_results[0])
    elif(region == 'bb_reg1'):
        folder_collection[region]["VCASB"].append(bb_VCASB[1])
        folder_collection[region]["results"].append(bb_results[1])
    elif(region == 'bb_reg2'):
        folder_collection[region]["VCASB"].append(bb_VCASB[2])
        folder_collection[region]["results"].append(bb_results[2])
    elif(region == 'bb_reg3'):
        folder_collection[region]["VCASB"].append(bb_VCASB[3])
        folder_collection[region]["results"].append(bb_results[3])
        
# end function read_files

# main

if(len(sys.argv)<2):
    print("please provide either THR or FHR as argument")
    quit()
else:
    measurement = sys.argv[1]
    print(f"measurement type: {measurement}")
    if(measurement == "FHR"):
        measNameForFolder = 'FakeHitRateScan'
        measNameForJSON = 'FakeHitRate'
        folder_collection = region_collection_FHR
    elif(measurement == "THR"):
        measNameForFolder = 'ThresholdScan'
        measNameForJSON = 'Threshold average per region'
        folder_collection = region_collection_THR
    else:
        print("please provide either THR or FHR as argument")
        quit()
    
for region in folder_collection: # in each step, different region(s)' VCASB was varied

    print(f"VARIED REGION(s): {region}")
    file_path = os.path.join( base_path, measNameForFolder, folder_collection[region]['collection_folder'])
    #file_path = f"{base_path}/{measNameForFolder}/{folder_collection[region]['collection_folder']}/"
    folders_bytes = subprocess.check_output(f"ls {file_path}", shell=True)
    folders_string = folders_bytes.decode()
    folders_list = folders_string.split("\n")
    folders_list.pop() # it has one empty item at the end

    
    for results_folder in folders_list:  # each results_folder has results from a different VCASB setting
    
        #config_fileName = f"{file_path}/{results_folder}/config/scan_config.json5"
        config_fileName = os.path.join( file_path, results_folder, "config", "scan_config.json5")
        #results_fileName = f"{file_path}/{results_folder}/analysis/analysis_result.json5"
        results_fileName = os.path.join( file_path, results_folder, "analysis", "analysis_result.json5")
        if(debug): print(f"file path: {results_fileName}")
        read_files(config_fileName, results_fileName, measNameForJSON, debug)



# plot from folder_collection, which was copied from region_collection
if(debug): print(folder_collection['tb_reg0']["VCASB"])
if(debug): print(folder_collection['tb_reg0']["results"])

if(plot):

    plt.xlabel('VCASB')
    plt.xlim(50, 120)
    plt.ylabel(measurement)

    for region in folder_collection:  # replace by region_collection_THR when not having all data
    
        plt.plot(folder_collection[region]["VCASB"], folder_collection[region]["results"], label=region, linestyle='', marker='o', color=folder_collection[region]["color"], alpha = 0.5)
        
   
    if(measurement=='FHR'):
        plt.legend(loc="upper left")
        plt.yscale('log')  # symlog
        plt.savefig(f"./plots/FHR.png", dpi=300)
    elif(measurement=='THR'):
        plt.legend(loc="lower left")
        plt.savefig(f"./plots/THR.png", dpi=300)

if(csv):

    plt.figure()  # Reset figure to prevent multiple plots
    # Define VCASB values from 61 to 115 with step 3
    vcasb_values = list(range(61, 116, 3))

    # Define regions
    regions = ["tb_reg0", "tb_reg1", "tb_reg2", "tb_reg3", "bb_reg0", "bb_reg1", "bb_reg2", "bb_reg3"]

    # Create an empty DataFrame with predefined VCASB values
    df = pd.DataFrame({"VCASB/Region": vcasb_values})

    # Fill in results for each region
    for region in regions:
        # Get VCASB, results
        region_data = pd.DataFrame({
            "VCASB/Region": folder_collection[region]["VCASB"],
            region: folder_collection[region]["results"]
        })
        # Merge based on VCASB, NaN if empty
        df = df.merge(region_data, on="VCASB/Region", how="left")

    # Save as CSV
    csv_fname = f"{measurement}_summary.csv"
    df.to_csv(os.path.join(base_path, csv_fname), index=False)
    #df.to_csv(os.path.join(".", csv_fname), index=False)

    # Plot(for debuging)
    for region in regions:
        plt.plot(df["VCASB/Region"], df[region], linestyle='', marker='o', label=region, color=folder_collection[region]["color"], alpha = 0.5)

    plt.xlabel('VCASB')
    plt.xlim(50, 120)
    plt.ylabel(measurement)
    plt.yscale('log') if measurement == 'FHR' else None  # Log scale only for FHR

    # Move legend outside the condition
    plt.legend(loc="upper left" if measurement == 'FHR' else "lower left")

    # Save figure
    plt.savefig(f"./plots/{measurement}_from_df.png", dpi=300)


