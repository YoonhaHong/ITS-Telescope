#!/usr/bin/env python3

import logging
import argparse
import datetime
from mlr1daqboard import pico_daq
from dpts_fhr import fhr_scan
import dpts_helpers as helpers

if __name__=="__main__":
    parser = argparse.ArgumentParser("DPTS source measurement", formatter_class=argparse.ArgumentDefaultsHelpFormatter,add_help=False)
    source_group = parser.add_argument_group('Source arguments', 'The arguments (and default values) unique to the source measurement.')
    source_group.add_argument("--ntrg", type=int, default=10000, help="Total number of triggers.")
    source_group.add_argument("--trg_ch", "--ch", default="AUX", help="Trigger channel. Hint: for source scan, it is best to trigger on the CML output.")
    source_group.add_argument("--trg_wait", type=int, default=0, help="Time in us before auto trigger fires (0=inf).")
    source_group.add_argument("--nseg", type=int, default=100,   help="Number of picoscope segments (ntrg is divided in trains of nseg triggers)")
    source_group.add_argument('--mask-pixel', '-m', nargs=2, type=int, default=[], action='append', help='Pixel (col and row) to mask out. Can be used multiple times.')
    helpers.add_common_scan_args(parser)
    helpers.add_common_args(parser)
    args = parser.parse_args()

    if args.config_json is not None:   
        helpers.load_json_args(parser, args)
    
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    helpers.setup_logging(args,now)
    helpers.finalise_args(args)

    daq = pico_daq.ScopeAcqPS6000a(trg_ch=args.trg_ch,trg_mV=50,npre=10,npost=600000,
            auto_trigger_us=args.trg_wait, nsegments=args.nseg)

    fhr_scan(args,daq=daq,now=now)

