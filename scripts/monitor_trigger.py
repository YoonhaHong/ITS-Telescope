#!/usr/bin/env python3

import json
import argparse
import os,sys
import datetime

def readjson():
    with open(args.json,'r',encoding='utf-8') as file:
        jsonconfig = json.load(file)
    return jsonconfig

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trigger board monitoring",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--json',help='Json file to initialize',default="./json/trigger_board.json")
    parser.add_argument('--dt',type=float,help='Time resolution')
    parser.add_argument('--log','-l',action='store_true',help='Create log file')
    args=parser.parse_args()

    jsonconfig = readjson()
    sw_path = jsonconfig['SW_path']
    monitor = jsonconfig['Monitor']
    monitor_ch = jsonconfig['Monitor_ch']
    nevents = jsonconfig['Nevents']
    port = jsonconfig['Port']
#    log_sw = jsonconfig['Log']
    log_path = jsonconfig['Log_path']
    
    now = datetime.datetime.now()
    filename = 'trglog-%s.log'%(now.strftime('%Y%m%d_%H%M%S'))

    if args.log:
        if args.dt:
            cmd = "sudo python3 -u " + os.path.join(sw_path, monitor) +  " {} -n {} -p {} --dt {} | tee {}".format(monitor_ch,nevents,port,args.dt,os.path.join(log_path,filename))
        else:
            cmd = "sudo python3 -u " + os.path.join(sw_path, monitor) +  " {} -n {} -p {} | tee {}".format(monitor_ch,nevents,port,os.path.join(log_path,filename))
#            cmd = "sudo " + os.path.join(sw_path, monitor) +  " {} -n {} -p {}".format(monitor_ch,nevents,port)


    else:
        if args.dt:
            cmd = "sudo " + os.path.join(sw_path, monitor) +  " {} -n {} -p {} --dt {}".format(monitor_ch,nevents,port,args.dt)
        else:
            cmd = "sudo " + os.path.join(sw_path, monitor) +  " {} -n {} -p {}".format(monitor_ch,nevents,port)


    os.system(cmd)


