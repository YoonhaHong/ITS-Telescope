#!/usr/bin/env python3

from mlr1daqboard import APTSDAQBoard
import datetime
import logging
import argparse
import os
from tqdm import tqdm
from time import sleep
import json
import apts_helpers as helpers

def apts_readout(args):
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
    daq.set_vdac('AP_VRESET', args.vreset)
    if args.mux!=-1:
        daq.set_mux(args.mux)
    else:
        logging.info(f"Not setting multiplexer selection, as args.mux = {args.mux}")
    if args.pulse!=None: daq.set_pulse_sel(sel0=(args.pulse&1),sel1=((args.pulse>>1)&1))
    daq.configure_readout(trg_type=args.trg_type,trg_thr=args.trg_thr,pulse=(args.pulse!=None),n_frames_before=args.n_frames_before, n_frames_after=args.n_frames_after,sampling_period=args.sampling_period)
    if args.trg_pixels!=None: daq.set_internal_trigger_mask(trg_pixels=args.trg_pixels,mux=True if args.mux in range(4) else False)
    logging.info(f"DAC values setting, waiting {args.expert_wait} seconds for Ia current to stabilize...") #FIXME verify
    for _ in range(args.expert_wait):
        logging.info(f"   Ia = {daq.read_isenseA():0.2f} mA")
        sleep(1)

    logging.info('Starting readout')
    with open(os.path.join(args.output_dir,args.fname+".raw"),'wb') as outfile:
        for itrg in tqdm(range(args.ntrg),desc='Trigger'):
            data=daq.read_event(timeout=100000)
            outfile.write(data)
    logging.info('Done')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APTS readout",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--ntrg'   ,'-n',type=int,help='number of triggers',default=1000)
    parser.add_argument('--trg_type','-ty',default=1, help='trigger: ext, int',type=lambda t: {'ext':0,'int':1}[t])
    parser.add_argument('--trg_thr','-tt',type=int,help='auto trigger threshold in ADC counts (default=20)',default=20)
    parser.add_argument('--vbb_array','-vbbr', nargs='+', type=float, default= [0.0, 0.6, 1.2, 1.8, 2.4, 3.6, 4.8], help='Only for bookkeeping (no effect): Array of Vbb values (ex.: -vbbr 0. 1.4 2 ).')
    parser.add_argument('--prefix',default='apts_',help='Output file prefix')
    helpers.add_common_args(parser)
    args = parser.parse_args()

    now = datetime.datetime.now()
    
    if args.serial:
        args.fname = f"{args.prefix}{args.serial}_{now.strftime('%Y%m%d_%H%M%S')}{args.suffix}"
    else:
        args.fname = f"{args.prefix}{now.strftime('%Y%m%d_%H%M%S')}{args.suffix}"

    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                       filename=os.path.join(args.output_dir,args.fname+".log"),filemode='w')
    log_term = logging.StreamHandler()
    log_term.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    log_term.setLevel(logging.INFO)
    logging.getLogger().addHandler(log_term)

    logging.debug(f"Running {os.path.basename(__file__)} with arguments:\n{json.dumps(vars(args),indent=4)}")
    
    helpers.finalise_args(args)

    try:
        apts_readout(args)
    except KeyboardInterrupt:
        logging.info('User stopped.')
    except Exception as e:
        logging.exception(e)
        logging.fatal('Terminating!')

