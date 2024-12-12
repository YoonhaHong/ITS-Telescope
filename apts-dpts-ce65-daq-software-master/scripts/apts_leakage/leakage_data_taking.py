#!/usr/bin/env python3
import numpy as np
import datetime
import logging
from pathlib import Path
import argparse
import os
from tqdm import tqdm
from time import sleep
import sys
sys.path.append('../../apts/')
sys.path.append('../../analysis/apts/')
import apts_readout
import apts_helpers as helpers
import json

def data_taking(args):
    now = datetime.datetime.now()
    if args.serial:
        args.fname = f"{args.prefix}{args.serial}_{now.strftime('%Y%m%d_%H%M%S')}_{args.chip_ID}_vh{int(args.vh)}_vr{int(args.vreset)}_vbb{int(args.vbb*1000)}_ir{int(args.ireset*1000)}_T{int(args.Temp)}{args.suffix}"
    else:
        args.fname = f"{args.prefix}{now.strftime('%Y%m%d_%H%M%S')}_{args.chip_ID}_vh{int(args.vh)}_vr{int(args.vreset)}_vbb{int(args.vbb*1000)}_ir{int(args.ireset*1000)}_T{int(args.Temp)}{args.suffix}"

    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',filename=os.path.join(args.output_dir,args.fname+".log"),filemode='w')
    log_term = logging.StreamHandler()
    log_term.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    log_term.setLevel(logging.INFO)
    logging.getLogger().addHandler(log_term)

    logging.debug(f"Running {os.path.basename(__file__)} with arguments:\n{json.dumps(vars(args),indent=4)}")
    helpers.finalise_args(args)
    try:
        apts_readout.apts_readout(args)
    except KeyboardInterrupt:
        logging.info('User stopped.')
    except Exception as e:
        logging.exception(e)
        logging.fatal('Terminating!')

if __name__ == "__main__":
    default_data_dir = os.path.realpath(os.path.join(os.path.dirname(__file__),"../../Data"))
    
    parser = argparse.ArgumentParser(description="All scripts for data taking and analysis")
    # chip_ID
    parser.add_argument('--ntrg'   ,'-n',type=int,help='number of triggers',default=1000)
    parser.add_argument('--trg_type','-ty',default=1, help='trigger: ext, int',type=lambda t: {'ext':0,'int':1}[t])
    parser.add_argument('--trg_thr','-tt',type=int,help='auto trigger threshold in ADC counts (default=20)',default=20)
    parser.add_argument('--vbb_array','-vbbr', nargs='+', type=float, default= [0.0, 0.6, 1.2, 1.8, 2.4, 3.6, 4.8], help='Only for bookkeeping (no effect): Array of Vbb values (ex.: -vbbr 0. 1.4 2 ).')
    parser.add_argument('--prefix',default='apts_',help='Output file prefix')
    parser.add_argument('--Temp', default=30, type=float,help='Temperature of the sensor in degree Celsius')
    #other
    parser.add_argument('--vbb',type=float, help='Only for bookkeeping (no effect): Bias voltage applied in unit of V (e.g. 0 , 1.2 ,...).')
    helpers.add_common_args(parser)
    args = parser.parse_args()
    helpers.finalise_args(args)
    
    data_taking(args)
