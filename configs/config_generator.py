import argparse
import configparser
import sys
import os
import pandas as pd
sys.path.append( "../scripts_labtest")
from vcasb2threshold import extract_vcasb_threshold, draw_vcasb_threshold

def modify_vcasb_values(args, threshold, df):
    config = configparser.ConfigParser(allow_no_value=True, delimiters=("=", ":"))
    config.optionxform = str  # 대소문자 구분
    config.read(args.input_conf)

    section = "Producer.MOSSRAISER_0"
    if section in config:
        for key in config[section]:
            if "VCASB" in key:
                region_index = key[0:2] + key[9]
                new_vcasb = df[df['threshold']==threshold][region_index].iloc[0]
                config[section][key] = str(new_vcasb)

    else:
        print(f"Section [{section}] not found in {args.input_conf}.")
    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modify VCASB values in a .conf file and save to a new file.")
    parser.add_argument(
        "-i", "--input_conf", 
        type=str, 
        default="./templates/template.conf", 
        help="Path to the input_conf file. Default is './templates/template.conf'."
    )
    parser.add_argument(
        "-s", "--scan",
        type=str,
        default="/Users/yoonha/cernbox/babyMOSS-2_4_W21D4/ThresholdScan/ScanCollection_20241126_113714",
        help="ScanCollection folder for VCASB value."
    )
    parser.add_argument(
        "-T", "--threshold",
        type=int, nargs=2, 
        default = [10, 30],
        help="Range for threshold"
    )
    
    args = parser.parse_args()

    df_all_results = extract_vcasb_threshold(args.scan)
    fit_parameters = draw_vcasb_threshold(df_all_results, fig=False)

    arr_thr_vcasb = []
    for threshold in range(args.threshold[0], args.threshold[1], 1):
        for_each_thr = {}
        for_each_thr['threshold'] = threshold
        for region, value in fit_parameters.items():
            vcasb = (threshold - fit_parameters[region]['intercept']) / fit_parameters[region]['slope']
            for_each_thr[region] = int(vcasb)
        arr_thr_vcasb.append( for_each_thr )
    
    df_thr = pd.DataFrame(arr_thr_vcasb)
    print(df_thr.head(5))
    #print(df_thr[df_thr['threshold']==12]['tb0'].iloc[0])

    input_name = os.path.basename( args.input_conf )[:-5]
    if not os.path.exists(input_name): os.mkdir(input_name)
    print( f"Saving at dir {input_name}")

    for thr in range( args.threshold[0], args.threshold[1], 1):
        config = modify_vcasb_values( args, thr, df_thr )
        with open(f"{input_name}/{input_name}_THR{thr}.conf", "w") as file:
            config.write(file, space_around_delimiters=False)
    