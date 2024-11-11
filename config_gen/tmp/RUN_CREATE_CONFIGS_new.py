#! /usr/bin/env python3
from create_configs import create_configs
import argparse

# Top level output directories #########
OUTPUT_CONFIG_DIR='/home/palpidefs/testbeam/TB_July_2024/eudaq_configs' # Top level testbeam config dir
OUTPUT_DATA_DIR='/home/palpidefs/testbeam/TB_July_2024/data' # Top level testbeam data dir
TOP_RESULT_DIR=None # This should be 'None' if not used
########################################

# Templates paths ############
EUDAQ2_TEMPLATE='/home/palpidefs/testbeam/TB_July_2024/config_gen/templates/babyMOSS_template.conf'
MOSS_TESTING_TEMPLATE='/home/palpidefs/testbeam/TB_July_2024/config_gen/templates/scan_config_template.json'
##############################

# General MOSS settings ######
DEVICE_NAME='babyMOSS-2_2_W21D4'
HALF_UNIT='tb'
TS_CONFIG_PATH='/home/palpidefs/testbeam/TB_July_2024/sw/config/ts_config_raiser.json5'
NEVENTS=100000
REGION_ENABLED=0b1111
IBIAS=62
IBIASN=100
IDB=50	
IRESET=10
VSHIFT=145
VCASN=104
BANDGAP_TRIM_TOP=[0xf8, 0x99, 0xa8, 0x8a] #TOP-HU
BANDGAP_TRIM_BOT=[0x9b, 0xac, 0xbb, 0xac] #BOT-HU
##############################

# VCASB #######################
REGION_TO_MODIFY=3
START=8
STOP=28 #exclusive!
STEP=2
VCASB_RANGE=(START, STOP, STEP)
VCASB_DEFAULT=80 #To be set to all other regions
###############################

# Lower level output directoreis ####
SETTINGS_DIR="psub12_allregions_idb50" #Used to create sub directory suffix to HALF_UNIT for storing files !!!SHOULD BE CHANGED!!!
OUTPUT_NAME_PREFIX=None # Prefix to the generated files 

def OUTPUT_DIR():
    return f'{OUTPUT_CONFIG_DIR}/{DEVICE_NAME}/{HALF_UNIT}_{SETTINGS_DIR}/region{REGION_TO_MODIFY}'
#####################################

# Disable directory creating ########
CREATE_EUDAQ_DATA_DIR=True
#####################################

# Delete previous config files ######
OVERWRITE_CONFIGS=False
if OVERWRITE_CONFIGS:
    import os 
    command = f'rm -r {OUTPUT_DIR}/*'
    os.system(command)
#####################################

def config_call(args = None):
    """helper function to reduce size. Calls config function and sets Bandgap trimming to corresponding values"""
    if HALF_UNIT == 'tb':
        BANDGAP_TRIM=BANDGAP_TRIM_TOP
    elif HALF_UNIT == 'bb':
        BANDGAP_TRIM=BANDGAP_TRIM_BOT
    create_configs(
    eudaq2_template=EUDAQ2_TEMPLATE,
    moss_testing_template=MOSS_TESTING_TEMPLATE,
    device_name=DEVICE_NAME,
    half_unit=HALF_UNIT,
    ts_config_path=TS_CONFIG_PATH,
    top_result_dir=TOP_RESULT_DIR, # <-- here
    nevents=NEVENTS,
    region_enabled=REGION_ENABLED if not args.disable_regions else get_region_enabled(), 
    ibias=IBIAS,
    ibiasn=IBIASN,
    idb=IDB,
    ireset=IRESET,
    vshift=VSHIFT,
    vcasn=VCASN,
    bandgap_trim=BANDGAP_TRIM,
    region=REGION_TO_MODIFY,
    vcasb_range=VCASB_RANGE,
    vcasb_default=VCASB_DEFAULT,
    output_dir=OUTPUT_DIR(),
    settings_dir=SETTINGS_DIR,
    output_name_prefix=OUTPUT_NAME_PREFIX,
    create_eudaq_data_dir=CREATE_EUDAQ_DATA_DIR
    )

def get_region_enabled():
    """disables other regions in REGION_ENABLED"""
    return 1<<(REGION_TO_MODIFY)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a set of config files for VCASB scan. Either for a full scan or for a specific region for one or both HUs. Both eudaq2 and moss testing configs are created.")
    parser.add_argument('--vcasb_range', '-vs', type=int, nargs=3, help="Three values used to generating the VCASB range. Syntax: (start, stop, step). NOTE: 'stop' is exclusive.")
    parser.add_argument('--region', '-r', type=int, help="Region to modify vcasb.")
    parser.add_argument('--half_unit', '-hf', default=None, help="Half unit to be enabled. (tb or bb or both)")
    parser.add_argument('--disable_regions', '-dr', action="store_true", help="Disable other regions for HU")
    parser.add_argument('--full_scan','-fs',action="store_true", help="Scan both HUs and all regions. Dont specifiy region or HU.")    
    args = parser.parse_args()
    if args.vcasb_range is not None:
        VCASB_RANGE=args.vcasb_range
    if args.full_scan:
        for hu in ["tb","bb"]:
            HALF_UNIT=hu
            for r in [0,1,2,3]:
                REGION_TO_MODIFY=r
                config_call(args)
        print("\nFull Telescope Folder/Files Created")
        exit()

    if args.region is not None:
        REGION_TO_MODIFY=args.region

    if args.half_unit is not None:
        if args.half_unit == 'both':
            for hu in ["tb","bb"]:
                HALF_UNIT=hu
                config_call(args)
        elif args.half_unit == 'tb' or args.half_unit == 'bb':
            HALF_UNIT=args.half_unit
            config_call(args)
    else:
        config_call(args)



    


                


    
