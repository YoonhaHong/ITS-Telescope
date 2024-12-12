#! /usr/bin/env python3
from mlr1daqboard import DPTSDAQBoard
import logging
import argparse
import datetime
import os
import dpts_helpers as helpers

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Script for powering the DPTS.", formatter_class=argparse.ArgumentDefaultsHelpFormatter,add_help=False)
    power_group = parser.add_argument_group('DPTS power arguments', 'The arguments (and default values) unique to the DPTS power script.')
    power_group.add_argument('--vh', default=600, type=float, help='VH in mV')
    helpers.add_common_args(parser)
    parser.add_argument('state',metavar="ON/OFF",choices=['ON','OFF','on','off'],help='ON or OFF')
    args = parser.parse_args()
    
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    if args.config_json is not None:   
        helpers.load_json_args(parser, args)
    
    #helpers.setup_logging(args,now)
    helpers.finalise_args(args)

    try:
        daq = DPTSDAQBoard(calibration=args.proximity,serial=args.serial)
        if args.state.upper()=="ON":
            daq.power_on()
            daq.set_dacs(args,vh=True)
        else:
            daq.power_off()
        logging.info('Powered '+args.state.upper())
    except KeyboardInterrupt:
        logging.info('User stopped.')
    except Exception as e:
        logging.exception(e)
        logging.fatal('Terminating!')
