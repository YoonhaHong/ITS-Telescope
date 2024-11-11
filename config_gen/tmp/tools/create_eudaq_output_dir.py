#! /usr/bin/env python3

import configparser
import argparse
import os

def get_conf_from_ini(ini_file):
    iniConfig = configparser.ConfigParser()
    iniConfig.read(ini_file)
    config_path_list = iniConfig.get('RunControl', 'configs').split(',')    
    return config_path_list

def get_output_dir_from_conf(confConfig):
    data_path = confConfig.get('DataCollector.dc','EUDAQ_FW_PATTERN')      
    data_path, file = os.path.split(data_path)
    return data_path

def create_output_dir(ini_file=None, conf_files=None):
    config_path_list = []
    if ini_file is not None: config_path_list = config_path_list + get_conf_from_ini(ini_file)
    if conf_files is not None: config_path_list = config_path_list + conf_files
    for config_path in config_path_list:
        confConfig = configparser.ConfigParser()
        confConfig.read(config_path)
        data_path = get_output_dir_from_conf(confConfig)
        if not os.path.exists(data_path):
            os.makedirs(data_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Creates output directories as specified in eudaq2 .conf files. The output directories can be extracted from either one .ini files, several .conf files, or both.")
    parser.add_argument('--ini_file', '-i', default=None, help="eudag2 .ini file. Config files are extracted from the .ini file, and the output directories er extracted from the .conf files.")
    parser.add_argument('--conf_files', '-c', default=None, nargs='*', help="Any number of .conf. The output directories are extracted the extracted from the .conf files.")
    args = parser.parse_args()

    run_list = create_output_dir(args.ini_file, args.conf_files)


    
