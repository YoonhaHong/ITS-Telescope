#!/usr/bin/env python3

import argparse
import datetime
from dpts_threshold import threshold_scan
import dpts_helpers as helpers

if __name__=="__main__":
    parser = argparse.ArgumentParser("DPTS decoding calibration", formatter_class=argparse.ArgumentDefaultsHelpFormatter,add_help=False)
    decode_group = parser.add_argument_group('Decoding calibration arguments', 'The arguments (and default values) unique to the decoding calibration.')
    decode_group.add_argument("--ninj", type=int, default=100, help="Number of injections per pixel.")
    decode_group.add_argument("--vh", type=int, default=600, help="VH in mV")
    decode_group.add_argument("--rows", type=int, default=[], nargs="*", help="Rows to scan.")
    decode_group.add_argument("--cols", type=int, default=[], nargs="*", help="Rows to scan.")
    helpers.add_common_scan_args(parser)
    helpers.add_common_args(parser)
    args = parser.parse_args()

    if args.config_json is not None:   
        helpers.load_json_args(parser, args)
    
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    helpers.setup_logging(args,now)
    helpers.finalise_args(args)
    
    if not args.rows: args.rows = list(range(32))
    if not args.cols: args.cols = list(range(32))
    args.vmax=args.vh
    args.vmin=args.vh
    args.vstep=args.vh

    args.vsteps = list(range(args.vmin, args.vmax+args.vstep, args.vstep))
    
    threshold_scan(args,now=now)
