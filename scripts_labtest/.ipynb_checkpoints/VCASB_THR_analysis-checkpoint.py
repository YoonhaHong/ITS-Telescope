import argparse
import json5
import os
import glob
import csv
import configparser

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

fit_parameters = {}

# Function to process each folder and extract VCASB and Thresholds
def process_folder(folder_path):
    # Paths to the JSON files
    config_file = os.path.join(folder_path, "config", "scan_config.json5")
    analysis_file = os.path.join(folder_path, "analysis", "analysis_result.json5")
    
    if not os.path.exists(config_file) or not os.path.exists(analysis_file):
        print(f"Missing files in folder: {folder_path}")
        return None
    
    # Load scan_config.json5
    with open(config_file, 'r') as f:
        config_data = json5.load(f)
    
    # Extract VCASB values from the config
    vcasb_tb = config_data['moss_dac_settings']['tb']['VCASB']
    vcasb_bb = config_data['moss_dac_settings']['bb']['VCASB']
    
    # Load analysis_result.json5
    with open(analysis_file, 'r') as f:
        analysis_data = json5.load(f)
    
    # Extract Threshold averages for each region from 'tb' and 'bb'
    threshold_tb = analysis_data['tb']['Threshold average per region']
    threshold_bb = analysis_data['bb']['Threshold average per region']
    
    # Combine the results for each region
    results = []
    for region_index in range(len(vcasb_tb)): 
        result = {
            
            'VCASB':        vcasb_tb[region_index],
            'region':       f"tb{region_index}",
            'Threshold':    threshold_tb[region_index]
        }
        results.append(result)
    for region_index in range(len(vcasb_bb)): 
        result = {
            
            'VCASB':        vcasb_bb[region_index],
            'region':       f"bb{region_index}",
            'Threshold':    threshold_bb[region_index]
        }
        results.append(result)
    

    return results

# Main function to iterate over all folders and process them
def extract_vcasb_threshold(scan_collection_folder):
    # Get a list of all subdirectories that match the pattern 'babyMOSS-2_4_W21D4_ThresholdScan_*'
    scan_folders = glob.glob(os.path.join(scan_collection_folder, 'babyMOSS-2_4_W21D4_ThresholdScan_*'))
    
    all_results = []
    
    # Process each folder
    for folder in scan_folders:
        print(f"Processing folder: {folder}")
        results = process_folder(folder)
        if results:
            all_results.extend(results)
    
    # Save the results to a CSV file
    output_file = os.path.join(scan_collection_folder, "vcasb_threshold_results.csv")
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['VCASB', 'region', 'Threshold'])
        writer.writeheader()
        writer.writerows(all_results)
    
    print(f"Results saved to: {output_file}")
    return all_results

def draw_vcasb_threshold(scan_collection_folder):
    colors = {
        'tb0': 'red',
        'tb1': 'orange',
        'tb2': 'gold',
        'tb3': 'darkkhaki',
        'bb0': 'green',
        'bb1': 'blue',
        'bb2': 'indigo',
        'bb3': 'purple'
    }   
    global fit_parameters
    csv_file = os.path.join(scan_collection_folder, "vcasb_threshold_results.csv")
    data = pd.read_csv(csv_file)

    plt.figure(figsize=(10, 6))

    vcasb_values = sorted(data['VCASB'].astype(int).unique())

    regions_tb = [region for region in data['region'].unique() if 'tb' in region]
    regions_bb = [region for region in data['region'].unique() if 'bb' in region]

    # Plot for tb regions
    for region in regions_tb:
        region_data = data[data['region'] == region].sort_values(by='VCASB')
        x = region_data['VCASB']
        y = region_data['Threshold']
        region_color = colors.get(region, 'black')

        slope, intercept = np.polyfit(x, y, 1)
        fit_parameters[region] = {'slope': slope, 'intercept': intercept}

        plt.scatter(x, y, label=f'{region}: y = {slope:.2f}x + {intercept:.2f}', 
                    marker='o', color = region_color)
        plt.plot(x, slope*x + intercept, color = region_color)

    # Plot for bb regions
    for region in regions_bb:
        region_data = data[data['region'] == region].sort_values(by='VCASB')
        x = region_data['VCASB']
        y = region_data['Threshold']
        region_color = colors.get(region, 'black')

        slope, intercept = np.polyfit(x, y, 1)
        fit_parameters[region] = {'slope': slope, 'intercept': intercept}

        plt.scatter(x, y, label=f'{region}: y = {slope:.2f}x + {intercept:.2f}', 
                    marker='o', color = region_color)
        plt.plot(x, slope*x + intercept, color = region_color)


    # Adding title and labels
    plt.title('VCASB vs Threshold for Each Region', fontsize=14)
    plt.xlabel('VCASB', fontsize=12)
    plt.ylabel('Threshold', fontsize=12)

    # Display the legend
    plt.legend(title="Regions", loc='best')

    # Display the grid
    plt.grid(True)

    # Show the plot
    plt.tight_layout()
    plt.savefig("VCASB-THR.pdf")
    #plt.show()

def print_vcasb_each():
    threshold_range = range(10, 20, 1)
    print( f"Threshold \t region \t VCASBr" )
    for threshold in threshold_range:
        vcasb = (threshold - fit_parameters['tb0']['intercept']) / fit_parameters['tb0']['slope']
        print(f"Threshold = {threshold} \t tb0_VCASB = {vcasb:.0f}")

def save_vcasb_txt(outpath):
    threshold_range = range(10, 30, 1)
    txt_file = os.path.join( outpath, 'vcasb_values.txt' )
    with open(txt_file, 'w') as file:
        for threshold in threshold_range:
            file.write(f"##### THRESHOLD = {threshold} ######\n")
            for region, value in fit_parameters.items():
                vcasb = (threshold - fit_parameters[region]['intercept']) / fit_parameters[region]['slope']
                file.write(f"{region[0:2]}_region{region[-1]}_VCASB = {vcasb:.0f}\n") 
                            #tb_region0_VCASB = value
            file.write("\n\n")


    print(f"Saved as {txt_file}" )
    return fit_parameters
            



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract VCASB and Threshold values from ScanCollection folders")
    parser.add_argument('scan_collection_folder', type=str, help="Path to the ScanCollection folder")

    args = parser.parse_args()

    # Call the extraction function with the provided folder path
    extract_vcasb_threshold(args.scan_collection_folder)
    draw_vcasb_threshold(args.scan_collection_folder)
    save_vcasb_txt(".")

