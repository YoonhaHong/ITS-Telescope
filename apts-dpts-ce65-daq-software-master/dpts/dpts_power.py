#! /usr/bin/env python3
from mlr1daqboard import DPTSDAQBoard
import logging
import argparse
import os
import datetime
import json

default_data_dir = os.path.realpath(os.path.join(os.path.dirname(__file__),"../Data"))

parser = argparse.ArgumentParser(description="Simple example script for DPTS control")
parser.add_argument('proximity',metavar="PROXIMITY",help='Proximity card name (e.g. DPTS-001). The name must be in the same format as the corresponding calibration file.')
parser.add_argument('state',metavar="ON/OFF",choices=['ON','OFF','on','off'],help='ON or OFF')
parser.add_argument('--serial' ,'-s',help='serial number of the DAQ board')
parser.add_argument('--prefix',default='dpts_',help='Output file prefix')
parser.add_argument('--suffix',default='',help='Output file suffix')
parser.add_argument('--vcasb', '-vb',   type=float, help='VCASB in mV')
parser.add_argument('--vcasn', '-vn',   type=float, help='VCASN in mV')
parser.add_argument('--ireset', '-ir',  type=float, help='IRESET in uA')
parser.add_argument('--idb', '-id',     type=float, help='IDB in uA')
parser.add_argument('--ibias', '-ib',   type=float, help='IBIAS in uA')
parser.add_argument('--ibiasn', '-ibn', type=float, help='IBIASN in uA')
parser.add_argument('--output-dir','-o',default=default_data_dir,help='Directory for output files.')
args = parser.parse_args()

now = datetime.datetime.now()

if args.serial:
    fname = f"{args.prefix}{args.serial}_{now.strftime('%Y%m%d_%H%M%S')}{args.suffix}"
else:
    fname = f"{args.prefix}{now.strftime('%Y%m%d_%H%M%S')}{args.suffix}"

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   filename=os.path.join(args.output_dir,fname+".log"),filemode='w')
log_term = logging.StreamHandler()
log_term.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
log_term.setLevel(logging.INFO)
logging.getLogger().addHandler(log_term)

logging.debug(f"Running {os.path.basename(__file__)} with arguments:\n{json.dumps(vars(args),indent=4)}")

try:
    daq = DPTSDAQBoard(calibration=args.proximity,serial=args.serial)
    if args.state.upper()=="ON":
        daq.power_on()
    else:
        daq.power_off()
    if args.vcasb:  daq.set_vcasb(args.vcasb)
    if args.vcasn:  daq.set_vcasn(args.vcasn)
    if args.ireset: daq.set_ireset(args.ireset)
    if args.idb:    daq.set_idb(args.idb)
    if args.ibias:  daq.set_ibias(args.ibias)
    if args.ibiasn: daq.set_ibiasn(args.ibiasn)
    logging.info('Powered '+args.state.upper())
except KeyboardInterrupt:
    logging.info('User stopped.')
except Exception as e:
    logging.exception(e)
    logging.fatal('Terminating!')
