#!/usr/bin/env python3

from mlr1daqboard import APTSDAQBoard
import datetime
import logging
import argparse
import os
from tqdm import tqdm
from time import sleep
import json
from labequipment import HAMEG
import numpy as np
import apts_helpers as helpers

def apts_gain(args):

    os.makedirs(args.output_dir, exist_ok=True)
    vres_range = np.arange(20, 901, 10)

    with open(os.path.join(args.output_dir, args.fname+".json"),'w') as file_handle:
        json.dump(vars(args), file_handle, indent=4)

    daq = APTSDAQBoard(serial=args.serial,calibration=args.proximity)
    if daq.is_chip_powered() is False:
        logging.info("APTS was off --> turning ON")
        daq.power_on()
    
    daq.set_idac('CE_PMOS_AP_DP_IRESET', args.ireset)
    daq.set_idac('CE_COL_AP_IBIASN', args.ibiasn)
    daq.set_idac('AP_IBIASP_DP_IDB', args.ibiasp)
    daq.set_idac('CE_MAT_AP_IBIAS4SF_DP_IBIASF', args.ibias4)
    daq.set_idac('AP_IBIAS3_DP_IBIAS', args.ibias3)
    daq.set_vdac('CE_VOFFSET_AP_DP_VH', args.vh)
    daq.set_vdac('AP_VRESET', 20)
    if args.mux!=-1:
        daq.set_mux(args.mux)
    else:
        logging.info(f"Not setting multiplexer selection, as args.mux = {args.mux}")
    daq.configure_readout(n_frames_before=args.n_frames_before, n_frames_after=args.n_frames_after,sampling_period=args.sampling_period)
    logging.info(f"DAC values setting, waiting {args.expert_wait} seconds for Ia current to stabilize...")
    for _ in range(args.expert_wait):
        logging.info(f"   Ia = {daq.read_isenseA():0.2f} mA")
        sleep(1)

    logging.info('Starting readout')
    with open(os.path.join(args.output_dir,args.fname+".raw"),'wb') as outfile:
        for vres in vres_range:
            daq.set_vdac('AP_VRESET', vres)
            sleep(0.4)
            for itrg in tqdm(range(args.ntrg_vres),desc='Trigger'):
                data=daq.read_event()
                outfile.write(data)
    logging.info('Done')

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="APTS gain measurement")
    parser.add_argument('--vbb_scan', action='store_true' , help='Perform a scan of VBB')
    parser.add_argument('--vbb_array', '-vbb', nargs='+', type=float, default= [0.0, 0.3, 0.6, 0.9, 1.2, 2.4, 3.6,4.8], help='Array of Vbb values (ex.: --vbb [0.,1.4,2]). Default is [0.0, 0.3, 0.6, 0.9, 1.2, 2.4, 3.6,4.8].')
    parser.add_argument('--vbb_channel', '-c', type=int, help='Channel of the power supply connected to the VBB')
    parser.add_argument('--ntrg_vres'   ,'-nvres',type=int,help='number of triggers per vreset step',default=1000)
    parser.add_argument('--prefix',default='apts_gain_',help='Output file prefix. Default is apts_gain_.')
    parser.add_argument('--hameg-path','-hpath',default='/dev/hmp4040', help='Path to the HAMEG device. Default is /dev/hmp4040')
    helpers.add_common_args(parser)
    args = parser.parse_args()

    helpers.finalise_args(args)

    now = datetime.datetime.now()

    if args.serial:
        args.fname = f"{args.prefix}{args.serial}_{now.strftime('%Y%m%d_%H%M%S')}{args.suffix}"
    else:
        args.fname = f"{args.prefix}{now.strftime('%Y%m%d_%H%M%S')}{args.suffix}"
    
    if not args.output_dir:
        args.output_dir = f"../Data/{args.prefix}{now.strftime('%Y%m%d_%H%M%S')}{args.suffix}"

    os.makedirs(args.output_dir, exist_ok=True)
    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                       filename=os.path.join(args.output_dir,args.fname+".log"),filemode='w')
    log_term = logging.StreamHandler()
    log_term.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    log_term.setLevel(logging.INFO)
    logging.getLogger().addHandler(log_term)

    try:

        if args.vbb_scan:
            h=HAMEG(args.hameg_path)
            base_directory = args.output_dir
            assert args.vbb_channel in np.arange(1,h.n_ch+1), "The vbb channel number should be consistent with the power supply connections"

            for vbb in args.vbb_array:
                h.set_volt(args.vbb_channel,vbb)
                args.output_dir = os.path.join(base_directory,f"vbb_{vbb:.1f}")
                args.vbb = vbb
                apts_gain(args)
        else:
            apts_gain(args)
    except KeyboardInterrupt:
        logging.info('User stopped.')
    except Exception as e:
        logging.exception(e)
        logging.fatal('Terminating!')

