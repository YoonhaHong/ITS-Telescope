#! /usr/bin/env python3
from mlr1daqboard import DPTSDAQBoard
import logging
import argparse
import os
import datetime
from tqdm import tqdm
import json
from dpts_helpers import mask_pattern, pulse_pattern
import dpts_helpers as helpers

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Script for DPTS control: pulsing, masking, shift register testing.", formatter_class=argparse.ArgumentDefaultsHelpFormatter,add_help=False)
    ctrl_group = parser.add_argument_group('DPTS ctrl arguments', 'The arguments (and default values) unique to the DPTS ctl script.')
    ctrl_group.add_argument("--pulse", type=int, default=0, help="Number of pulses to send.")
    ctrl_group.add_argument("--test",  type=int, default=0, help="Number of test writes to shift register.")
    ctrl_group.add_argument('--pixel',nargs=2,type=int,default=[],help='Pixel (col and row) to select for pulsing.')
    ctrl_group.add_argument("--mc", type=lambda x: int(x, 16), default=0)
    ctrl_group.add_argument("--md", type=lambda x: int(x, 16), default=0)
    ctrl_group.add_argument("--mr", type=lambda x: int(x, 16), default=0)
    ctrl_group.add_argument("--cs", type=lambda x: int(x, 16), default=0)
    ctrl_group.add_argument("--rs", type=lambda x: int(x, 16), default=0)
    ctrl_group.add_argument('--vh', default=600, type=float, help='VH in mV')
    helpers.add_common_args(parser)
    args = parser.parse_args()
    
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    if args.config_json is not None:   
        helpers.load_json_args(parser, args)
    
    if args.pixel: args.pixel = [args.pixel]

    helpers.setup_logging(args,now)
    helpers.finalise_args(args)
    
    try:
        daq = DPTSDAQBoard(calibration=args.proximity,serial=args.serial)
        daq.set_dacs(args,vh=True)
        if args.test:
            patterns = [
                int('1'*32*5*3,2),
                int('0'*32*5*3,2),
                int('10'*16*5*3,2),
                int('01'*16*5*3,2)
            ]
            pbar = tqdm(total=len(patterns)*args.test,desc='Testing shift register')
            for p in patterns:
                daq.write_shreg_raw(p)
                daq.clear_shreg_fifo()
                for i in range(args.test):
                    daq.write_shreg_raw(p)
                    r = daq.read_shreg(decode=False)
                    if r!=p: logging.warning(f"SI != SO: {p:x} != {r:x}")
                    pbar.update()
            pbar.close()
        else:
            if args.pulse:
                cs,rs=pulse_pattern(args.pixel)
                mc,md,mr=mask_pattern()
            else:
                cs,rs=pulse_pattern()
                mc,md,mr=mask_pattern(args.pixel)
            mc|=args.mc
            md|=args.md
            mr|=args.mr
            cs|=args.cs
            rs|=args.rs
    
            daq.clear_shreg_fifo()
            daq.write_shreg(rs=rs|args.rs,mc=mc|args.mc,md=md|args.md,cs=cs|args.cs,mr=mr|args.mr)
            daq.read_shreg(decode=True)

        if args.pulse:
            logging.info("Pulsing...")
            daq.pulse(npulses=args.pulse,ncycles_low=10000,ncycles_high=10000)

        logging.info('Done')
    except KeyboardInterrupt:
        logging.info('User stopped.')
    except Exception as e:
        logging.exception(e)
        logging.fatal('Terminating!')
