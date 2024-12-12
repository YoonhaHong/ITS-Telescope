#!/usr/bin/env python3

from mlr1daqboard import APTSDAQBoard
import datetime
import logging
import argparse
import os
import apts_readout
import apts_gain
from labequipment import HAMEG
from tqdm import tqdm
from time import sleep
import json
import apts_helpers as helpers

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APTS readout", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--firmware','-fw', default='0x107E7316.bit', help='Version of FPGA firmware file(e.g.: 0x107E7316.bit).')
    parser.add_argument('--vbb_array','-vbbr', nargs='+', type=float, default= [0.0, 0.6, 1.2, 1.8, 2.4, 3.6, 4.8], help='Array of Vbb values (ex.: -vbbr 0. 1.4 2 ).')
    parser.add_argument('--daq_channel', '-daqc', type=int, help='Channel of the power supply connected to the DAQ (5V)')
    parser.add_argument('--vbb_channel', '-vbbc', type=int, help='Channel of the power supply connected to the VBB')
    parser.add_argument('--ntrg_vres'   ,'-nvres',type=int,help='number of triggers per vreset step',default=50)
    parser.add_argument('--ntrg'   ,'-n',type=int,help='number of triggers',default=150000)
    parser.add_argument('--trg_type','-ty',default=1, help='trigger: ext, int',type=lambda t: {'ext':0,'int':1}[t])
    parser.add_argument('--trg_thr','-tt',nargs='+', type=int, default= [33, 36, 36, 36, 36, 37, 39], help='Array of trigger thresholds, one for each vbb (ex.: -tt 33 36 39).')
    parser.add_argument('--prefix',default='apts_',help='Output file prefix')
    parser.add_argument('--hameg-path','-hpath',default='/dev/serial/by-id/usb-HAMEG_HAMEG_HO720_019603994-if00-port0', help='Path to the HAMEG device.')
    helpers.add_common_args(parser)
    args = parser.parse_args()
    
    helpers.finalise_args(args)

    
    h=HAMEG(args.hameg_path)
    h.set_volt(args.vbb_channel,0)
    h.set_volt(args.daq_channel,5)
    h.power(True,args.daq_channel)
    h.power(True,args.vbb_channel)
    sleep(4)
    os.system(f"../tools/mlr1-daq-program --fx3=../tools/fx3.img --fpga=../tools/{args.firmware}")
    

    try:
        if not args.output_dir:
            args.output_dir = f"../Data/{args.prefix}fe55{args.suffix}/{args.chip_ID}"
        base_directory = args.output_dir 
        now = []
        for i,vbb in enumerate(args.vbb_array):
            now.append(datetime.datetime.now())
            h.set_volt(args.vbb_channel,vbb)
            args.vbb = vbb
            args.output_dir = os.path.join(base_directory, f'{vbb:.1f}/gain')
            os.makedirs(args.output_dir, exist_ok=True)
            logging.getLogger().handlers.clear()
            if args.serial:
                 args.fname = f"{args.prefix}gain_{args.serial}_{now[i].strftime('%Y%m%d_%H%M%S')}{args.suffix}"
            else:
                args.fname = f"{args.prefix}gain_{now[i].strftime('%Y%m%d_%H%M%S')}{args.suffix}"
            logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                               filename=os.path.join(args.output_dir,args.fname+".log"),filemode='w')
            log_term = logging.StreamHandler()
            log_term.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            log_term.setLevel(logging.INFO)
            logging.getLogger().addHandler(log_term)
            apts_gain.apts_gain(args)
        
        input("Gain calibration done. Put on the source and press enter.")
        
        trg_thr = args.trg_thr

        for j,vbb in enumerate(args.vbb_array):
            h.set_volt(args.vbb_channel,vbb)
            args.vbb = vbb
            args.output_dir = os.path.join(base_directory, f'{vbb:.1f}/source')
            args.trg_thr = int(trg_thr[j])
            os.makedirs(args.output_dir, exist_ok=True)
            logging.getLogger().handlers.clear()
            if args.serial:
                args.fname = f"{args.prefix}{args.serial}_{now[j].strftime('%Y%m%d_%H%M%S')}{args.suffix}"
            else:
                args.fname = f"{args.prefix}{now[j].strftime('%Y%m%d_%H%M%S')}{args.suffix}"

            logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                               filename=os.path.join(args.output_dir,args.fname+".log"),filemode='w')
            log_term = logging.StreamHandler()
            log_term.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            log_term.setLevel(logging.INFO)
            logging.getLogger().addHandler(log_term)
            apts_readout.apts_readout(args)
    except KeyboardInterrupt:
        logging.info('User stopped.')
    except Exception as e:
        logging.exception(e)
        logging.fatal('Terminating!')

    h.power(False,args.daq_channel)
    h.power(False,args.vbb_channel)
    h.set_volt(args.vbb_channel,0)
