#!/usr/bin/env python3

import mlr1daqboard
import logging
import argparse
import os
import json
import opamp_helpers as helpers


parser = argparse.ArgumentParser(description="Script to power the chip on/off",formatter_class=argparse.ArgumentDefaultsHelpFormatter,add_help=False)
parser.add_argument('state',metavar="on/off",choices=['on','off'],type=str.lower,help='ON or OFF')
helpers.add_common_args(parser)
helpers.add_common_output_args(parser)
args = parser.parse_args()

logging.debug(f"Running {os.path.basename(__file__)} with arguments:\n{json.dumps(vars(args),indent=4)}")

apts = mlr1daqboard.APTSDAQBoard(serial=args.serial,calibration=args.proximity)

if args.state == 'on': apts.power_on()
else: apts.power_off()
