#!/usr/bin/env python3

import json
import argparse
import os,sys

def readjson():
    with open(args.json,'r',encoding='utf-8') as file:
        jsonconfig = json.load(file)
    return jsonconfig

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trigger board setting(Threshold & Logic)",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--json',help='Json file to initialize',default="./json/trigger_board.json")

    args=parser.parse_args()

    jsonconfig = readjson()
    
    thrs_list = jsonconfig['Threshold']
    port = jsonconfig['Port']
    sw_path = jsonconfig['SW_path']
    logic = jsonconfig['Logic']

    ### Threshold setting
    ch0_cmd = "sudo " + sw_path + "mcp4728.py -p {} -a 96 -c1 -v {}".format(port,thrs_list['ch0'])
    os.system(ch0_cmd)

    ch1_cmd = "sudo " + sw_path + "mcp4728.py -p {} -a 96 -c3 -v {}".format(port,thrs_list['ch1'])
    os.system(ch1_cmd)

    ch2_cmd = "sudo " + sw_path + "mcp4728.py -p {} -a 97 -c1 -v {}".format(port,thrs_list['ch2'])
    os.system(ch2_cmd)

    ch3_cmd = "sudo " + sw_path + "mcp4728.py -p {} -a 97 -c3 -v {}".format(port,thrs_list['ch3'])
    os.system(ch3_cmd)

    ### Set Logic
    logic_cmd = "sudo " + sw_path + "./settrg.py -p {} --trg='{}'".format(port,logic)
    os.system(logic_cmd)


