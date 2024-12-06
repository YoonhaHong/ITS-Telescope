import argparse
import configparser
import sys
import os
import pandas as pd
sys.path.append( "../scripts_labtest")
from vcasb2threshold import extract_vcasb_threshold, draw_vcasb_threshold

def modify_vcasb_values(conf, df, threshold, moss_idx):
    config = configparser.ConfigParser(allow_no_value=True, delimiters=("=", ":"))
    config.optionxform = str  # 대소문자 구분
    config.read( conf )

    section = f"Producer.MOSSRAISER_{moss_idx}"
    if section in config:
        for key in config[section]:
            if "VCASB" in key:
                new_vcasb = df[df['Threshold']==threshold][key[:-6]].iloc[0]
                config[section][key] = str(new_vcasb)

    else:
        print(f"Section [{section}] not found in {conf}.")
    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modify VCASB values in a .conf file and save to a new file.")
    parser.add_argument(
        "-i", "--input_conf", 
        type=str, 
        default="./templates/kek-2MOSS_thr_scan.conf", 
        help="Path to the input_conf file."
    )
    parser.add_argument(
        "-c", "--csv",
        type=str, nargs=2,
        default=["../scripts_labtest/babyMOSS-2_4_W21D4_vcasb_values.csv", "../scripts_labtest/babyMOSS-2_4_W21D4_vcasb_values.csv"],
        help="VCASB value of DUT0 & DUT1"
    )
    parser.add_argument(
        "-T", "--threshold",
        type=int, nargs=2, 
        default = [15, 30],
        help="Range for threshold"
    )
    
    args = parser.parse_args()
    df_thr = pd.read_csv( args.csv[0])
    print(df_thr.head(5))
    #print(df_thr[df_thr['threshold']==12]['tb0'].iloc[0])

    input_name = os.path.basename( args.input_conf )[:-5]
    if not os.path.exists(input_name): os.mkdir(input_name)
    print( f"Saving at dir {input_name}")

    for thr in range( args.threshold[0], args.threshold[1], 1):
        config = modify_vcasb_values( conf = args.input_conf,
                                      df = pd.read_csv(args.csv[0]),
                                      threshold = thr,
                                      moss_idx=0 )
        with open(f"{input_name}/{input_name}_THR{thr}.conf", "w") as file:
            config.write(file, space_around_delimiters=False)

        config = modify_vcasb_values( conf = f"{input_name}/{input_name}_THR{thr}.conf",
                                      df = pd.read_csv(args.csv[1]),
                                      threshold = thr,
                                      moss_idx=1 )
        with open(f"{input_name}/{input_name}_THR{thr}.conf", "w") as file:
            config.write(file, space_around_delimiters=False)
    