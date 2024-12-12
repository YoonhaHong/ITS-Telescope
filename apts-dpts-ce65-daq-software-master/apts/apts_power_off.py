#!/usr/bin/env python3

import mlr1daqboard
import logging
import argparse
import os
import datetime
import json

default_data_dir = os.path.realpath(os.path.join(os.path.dirname(__file__),"../Data"))

parser = argparse.ArgumentParser(description="Simple example script for APTS readout")
parser.add_argument('--serial' ,'-s',help='serial number of the DAQ board')
parser.add_argument("--log-level", default="DEBUG", help="Logging level.")
parser.add_argument('--prefix',default='apts_',help='Output file prefix')
parser.add_argument('--suffix',default='',help='Output file suffix')
parser.add_argument('--output-dir','-o',default=default_data_dir,help='Directory for output files.')
args = parser.parse_args()

now = datetime.datetime.now()

if args.serial:
    fname = f"{args.prefix}{args.serial}_{now.strftime('%Y%m%d_%H%M%S')}{args.suffix}"
else:
    fname = f"{args.prefix}{now.strftime('%Y%m%d_%H%M%S')}{args.suffix}"

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',filename=os.path.join(args.output_dir,fname+".log"),filemode='w')
log_term = logging.StreamHandler()
log_term.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
log_term.setLevel(logging.getLevelName(args.log_level.upper()))
logging.getLogger().addHandler(log_term)

logging.debug(f"Running {os.path.basename(__file__)} with arguments:\n{json.dumps(vars(args),indent=4)}")

apts = mlr1daqboard.APTSDAQBoard(serial=args.serial)
apts.power_off()

