import argparse
import json5
import os
import glob
import csv
import configparser

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


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
    noise_tb = analysis_data['tb']['Noise average per region']
    threshold_bb = analysis_data['bb']['Threshold average per region']
    noise_bb = analysis_data['bb']['Noise average per region']
    
    # Combine the results for each region
    results = []
    for region_index in range(len(vcasb_tb)): 
        result = {
            
            'VCASB':        vcasb_tb[region_index],
            'region':       f"tb{region_index}",
            'Threshold':    threshold_tb[region_index],
            'Noise':        noise_tb[region_index]
        }
        results.append(result)
    for region_index in range(len(vcasb_bb)): 
        result = {
            
            'VCASB':        vcasb_bb[region_index],
            'region':       f"bb{region_index}",
            'Threshold':    threshold_bb[region_index],
            'Noise':        noise_bb[region_index]
        }
        results.append(result)
    

    return results

# Main function to iterate over all folders and process them
def extract_vcasb_threshold(scan_collection_folder, csv=False):
    # Get a list of all subdirectories that match the pattern 'babyMOSS-2_4_W21D4_ThresholdScan_*'
    scan_folders = glob.glob(os.path.join(scan_collection_folder, 'babyMOSS-2_4_W21D4_ThresholdScan_*'))
    
    all_results = []
    
    # Process each folder
    for folder in scan_folders:
        #print(f"Processing folder: {folder}")
        results = process_folder(folder)
        if results:
            all_results.extend(results)
    
    # Save the results to a CSV file
    if csv:
        output_file = os.path.join(scan_collection_folder, "vcasb_threshold_results.csv")
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['VCASB', 'region', 'Threshold', 'Noise'])
            writer.writeheader()
            writer.writerows(all_results)
        print(f"Results saved to: {output_file}")

    return pd.DataFrame(all_results)

#def draw_vcasb_threshold(scan_collection_folder, print=False):
def draw_vcasb_threshold(data, fig=False):
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
    fit_parameters = {}
    #csv_file = os.path.join(scan_collection_folder, "vcasb_threshold_results.csv")
    #data = pd.read_csv(csv_file)

    plt.figure(figsize=(10, 6))

    vcasb_values = sorted(data['VCASB'].astype(int).unique())

    regions_tb = [region for region in data['region'].unique() if 'tb' in region]
    regions_bb = [region for region in data['region'].unique() if 'bb' in region]

    # Plot for tb regions
    for region in regions_tb:
        region_data = data[data['region'] == region].sort_values(by='VCASB')
        x = region_data['VCASB']
        y = region_data['Threshold']
        y_err = region_data['Noise']

        region_color = colors.get(region, 'black')


        coeffs = np.polyfit(x, y, deg=1) 
        fit_func = np.poly1d(coeffs)
        slope = coeffs[0]  
        intercept = coeffs[1]  
        fit_parameters[region] = {'slope': slope, 'intercept': intercept}

        y_fit = fit_func(x)
        residuals = (y - y_fit) / y_err
        chi2 = np.sum(residuals**2)
        ndf = len(x) - (1+1)
        chi2_ndf = chi2 / ndf

        plt.errorbar(x, y, yerr=y_err, 
                    label=f'{region}: y = {slope:.2f}x + {intercept:.2f}    chi2 = {chi2:.3f}', 
                    linestyle=' ', marker='o', color = region_color)
        plt.plot(x, fit_func(x), color = region_color)

    # Plot for bb regions
    for region in regions_bb:
        region_data = data[data['region'] == region].sort_values(by='VCASB')
        x = region_data['VCASB']
        y = region_data['Threshold']
        y_err = region_data['Noise']
        region_color = colors.get(region, 'black')

        coeffs = np.polyfit(x, y, deg=1) 
        fit_func = np.poly1d(coeffs)
        slope = coeffs[0]  
        intercept = coeffs[1]  
        fit_parameters[region] = {'slope': slope, 'intercept': intercept}

        y_fit = fit_func(x)
        residuals = (y - y_fit) / y_err
        chi2 = np.sum(residuals**2)
        #pearson = (y-y_fit)**2 / y_fit
        #chi2 = np.sum(pearson)
        ndf = len(x) - (1+1)
        chi2_ndf = chi2 / ndf

        plt.errorbar(x, y, yerr=y_err, 
                    label=f'{region}: y = {slope:.2f}x + {intercept:.2f}    chi2 = {chi2:.3f}', 
                    linestyle=' ', marker='o', color = region_color)
        plt.plot(x, fit_func(x), color = region_color)


    plt.title('VCASB vs Threshold for Each Region', fontsize=14)
    plt.xlabel('VCASB', fontsize=12)
    plt.ylabel('Threshold', fontsize=12)
    plt.ylim(5, 40)

    plt.legend(loc='best')

    plt.grid(True)
    plt.tight_layout()

    # Show the plot
    if(fig):
        fig_name = f"VASB-THR_{os.path.basename(args.scan_collection_folder)}.pdf"
        plt.savefig( fig_name )
        print(f"Saved as {fig_name}")
        plt.show()

    return fit_parameters



def save_vcasb_txt(outpath, fit_parameters):
    threshold_range = range(10, 30, 1)
    txt_file = os.path.join( outpath, 'vcasb_values.txt' )
    with open(txt_file, 'w') as file:
        for threshold in threshold_range:
            file.write(f"##### THRESHOLD = {threshold} ######\n")
            for region, value in fit_parameters.items():
                vcasb = (threshold - fit_parameters[region]['intercept']) / fit_parameters[region]['slope']
                file.write(f"{region[0:2]}_region{region[-1]}_VCASB = {int(vcasb)}\n") 
                            #tb_region0_VCASB = value
            file.write("\n\n")


    print(f"Saved as {txt_file}" )
            



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract VCASB and Threshold values from ScanCollection folders")
    parser.add_argument('scan_collection_folder', type=str, help="Path to the ScanCollection folder")

    args = parser.parse_args()


    all_results = extract_vcasb_threshold(args.scan_collection_folder)
    fit_parameters = draw_vcasb_threshold(all_results, fig=True)
    #save_vcasb_txt(".", fit_parameters)

