#!/usr/bin/env python3

from mlr1daqboard import APTSDAQBoard
import datetime
import logging
import argparse
import os
import time
from tqdm import tqdm
from time import sleep
import json
import apts_helpers as helpers
import matplotlib
import matplotlib.pyplot as plt
import numpy as np


def count_noise(daq,thr_waiting):
    start_time = time.time()
    counts= 0
    print(f"collecting data for {thr_waiting} sec")
    while (time.time()-start_time<thr_waiting):
        try:
            data=daq.read_event(thr_waiting*1000) #to convert to ms
            if data is not None:
                counts+=1
        except Exception as e:   #check which exception is rised during timeout error
            print(e)
            break
    return counts

def set_threshold(args, daq, threshold):

    daq.configure_readout(trg_type=args.trg_type,trg_thr=threshold,pulse=(args.pulse!=None),n_frames_before=args.n_frames_before, n_frames_after=args.n_frames_after,sampling_period=args.sampling_period)
    logging.info(f"Threshold was changed to {threshold}, waiting 1 second") #FIXME verify
    sleep(1)


def apts_threshold_scan_graph(args):


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
    if args.pulse!=None: daq.set_pulse_sel(sel0=(args.pulse&1),sel1=((args.pulse>>1)&1))
    if args.trg_pixels!=None: daq.set_internal_trigger_mask(trg_pixels=args.trg_pixels)

    logging.info(f"DAC was changed, waiting {args.expert_wait} seconds for Ia current to stabilize...") #FIXME verify
    for _ in range(args.expert_wait+1):  #args.expert_wait
        logging.info(f"   Ia = {daq.read_isenseA():0.2f} mA")
        sleep(1)




    x=[]
    y=[]

    for thr in range (args.thr_min,args.thr_max+1,args.thr_step):
        print(f"Analyzing thr {thr}")
        set_threshold(args,daq, thr)
        counts = count_noise(daq, args.thr_waiting)
        print(f"At {thr} we have {counts} counts")
        x.append(thr)
        y.append(1.*counts/args.thr_waiting)

    figure, (ax1,ax2) = plt.subplots(1,2)

    ax1.plot(x, y)
    ax1.set_title(f"Threshold scan at Vbb = {args.vbb_array[0]} V")
    ax1.set_xlabel("Threshold (ADC)")
    ax1.set_ylabel("Hz")

    ax2.plot(x, y)
    ax2.set_title(f"Zoom")
    ax2.set_xlabel("Threshold (ADC)")
    ax2.set_ylim([0, 2])

    filename = os.path.join(args.output_dir,args.fname+"_threshold.png")
    plt.savefig(filename)
    plt.show()

    np.savetxt(os.path.join(args.output_dir,args.fname+"_threshold.txt"), (np.array(x),np.array(y)))




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APTS threshold scan, recomended THR value corresponds to < 1 Hz of events",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('thr_min',metavar="THR_MIN", type=int, help='Starting threshold value for scan in ADC')
    parser.add_argument('thr_max', metavar="THR_MAX",type=int, help='Final threshold value for scan in ADC')
    parser.add_argument('thr_step', metavar="THR_STEP",type=int, help='Step for scan in ADC')
    parser.add_argument('--trg_type','-ty',default=1, help='trigger: ext, int',type=lambda t: {'ext':0,'int':1}[t])
    parser.add_argument('--prefix',default='apts_',help='Output file prefix')
    parser.add_argument('--thr_waiting', default= 10,type=int, help='Time to read events for one thr settings (sec)')
    parser.add_argument('--vbb_array','-vbbr', nargs='+', type=float, default= [0.0], help='Vbb value in the title of histogram')

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
        apts_threshold_scan_graph(args)
    except KeyboardInterrupt:
        logging.info('User stopped.')
