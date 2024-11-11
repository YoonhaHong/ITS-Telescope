#! /usr/bin/env python3

import argparse
import subprocess
import re

DOWNWARD_ARROW = u'\u2B07'
UPWARD_ARROW = u'\u2191'

def extract_vcasb(filename):
    match = re.search(r'VCASB(\d+)', filename)
    if match:
        return int(match.group(1))
    else:
        return float('inf')  # Return infinity if VCASB value is not found

def find_files(directory, file_name):
    command = ["find", directory, "-name", file_name, "-maxdepth" , '1']
    result = subprocess.run(command, capture_output=True, text=True)
    results = result.stdout.splitlines()
    return results

def get_configs(directories):
    output_string = ''
    for dir in directories:
        config_files = find_files(dir, file_name="*.conf*")
        config_files = sorted(config_files, key=extract_vcasb)
        for config in config_files:
            output_string = f"{output_string},{config}"
        output_string = output_string[1:] # Hack to remove the first comma 
    return output_string

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prints out a list in the terminal with absolute path to all config files in a given directory. Copy the list to the `config`filed in the .ini file.")
    parser.add_argument('DIRECTORY', type=str, nargs='*', help="Directories containing the config files. Any number of folders can passed, and the config files will be printed in the same order as the folders is given.")
    args = parser.parse_args()

    config_string = get_configs(args.DIRECTORY)
    print(f"{DOWNWARD_ARROW}{DOWNWARD_ARROW}{DOWNWARD_ARROW}{DOWNWARD_ARROW}COPY THIS STRING{DOWNWARD_ARROW}{DOWNWARD_ARROW}{DOWNWARD_ARROW}{DOWNWARD_ARROW}\n\n")
    print(config_string)
    print(f"\n\n{UPWARD_ARROW}{UPWARD_ARROW}{UPWARD_ARROW}{UPWARD_ARROW}COPY THIS STRING{UPWARD_ARROW}{UPWARD_ARROW}{UPWARD_ARROW}{UPWARD_ARROW}")