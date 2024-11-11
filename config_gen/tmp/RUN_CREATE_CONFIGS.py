#! /usr/bin/env python3
from create_configs import create_configs

# Top level output directories #########
OUTPUT_CONFIG_DIR='/home/lennart/testbeam/TB_August_2024/eudaq_configs' # Top level testbeam config dir
OUTPUT_DATA_DIR='/home/lennart/testbeam/TB_August_2024/data' # Top level testbeam data dir
TOP_RESULT_DIR=None # This should be 'None' if not used
########################################

# Templates paths ############
EUDAQ2_TEMPLATE='/home/lennart/Downloads/config_gen/templates/babyMOSS_template.conf'
MOSS_TESTING_TEMPLATE='/home/lennart/Downloads/config_gen/templates/scan_config_template.json'
##############################

# General MOSS settings ######
DEVICE_NAME='babyMOSS-2_2_W21D4'
HALF_UNIT='tb'
TS_CONFIG_PATH='/home/lennart/testbeam/TB_Augst_2024/eudaq_configs/ts_config_raiser_2_2_W21D4.json5'
NEVENTS=100000
REGION_ENABLED=0b1111
IBIAS=62
IBIASN=100
IDB=50 #25
IRESET=10
VSHIFT=192
VCASN=64
BANDGAP_TRIM=[0xf8, 0x99, 0xa8, 0x8a] #TOP-HU
#BANDGAP_TRIM=[0x9b, 0xac, 0xbb, 0xac] #BOT-HU
##############################

# VCASB #######################
REGION_TO_MODIFY=3
START=8
STOP=28 #exclusive!
STEP=2
VCASB_RANGE=(START, STOP, STEP)
VCASB_DEFUALT=15 #To be set to all regions other regions
###############################

# Lower level output directoreis ####
SETTINGS_DIR='data' #Used to create sub directory for storing files
OUTPUT_NAME_PREFIX=None # Prefix to the generated files 
OUTPUT_DIR=f'{OUTPUT_CONFIG_DIR}/{DEVICE_NAME}/{HALF_UNIT}/region{REGION_TO_MODIFY}'
#####################################

# Disable directory creating ########
CREATE_EUDAQ_DATA_DIR=False # changed from True -BaadeHals
#####################################

# Delete previous config files ######
OVERWRITE_CONFIGS=False
if OVERWRITE_CONFIGS:
    import os 
    command = f'rm -r {OUTPUT_DIR}/*'
    os.system(command)
#####################################

create_configs(
    eudaq2_template=EUDAQ2_TEMPLATE,
    moss_testing_template=MOSS_TESTING_TEMPLATE,
    device_name=DEVICE_NAME,
    half_unit=HALF_UNIT,
    ts_config_path=TS_CONFIG_PATH,
    top_result_dir=TOP_RESULT_DIR, # <-- here
    nevents=NEVENTS,
    region_enabled=REGION_ENABLED, 
    ibias=IBIAS,
    ibiasn=IBIASN,
    idb=IDB,
    ireset=IRESET,
    vshift=VSHIFT,
    vcasn=VCASN,
    bandgap_trim=BANDGAP_TRIM,
    region=REGION_TO_MODIFY,
    vcasb_range=VCASB_RANGE,
    vcasb_default=VCASB_DEFUALT,
    output_dir=OUTPUT_DIR,
    settings_dir=SETTINGS_DIR,
    output_name_prefix=OUTPUT_NAME_PREFIX,
    create_eudaq_data_dir=CREATE_EUDAQ_DATA_DIR
)
