#!/usr/bin/env python3

# Isabella Sanna, 03/2022, CERN
# Python script that acquires the data of all the scans of all paramters for APTS.

from mlr1daqboard import APTSDAQBoard
import datetime
import logging
import argparse
import os
from tqdm import tqdm
from time import sleep
import numpy as np

def make_range(array):    #function used to create a range starting from minimum, maximum and step value given in input
    start,end,step=list(map(float, array))
    return np.arange(start, end+(step/2), step)

default_data_dir = os.path.realpath("../../../Data/scan_operating_point")

parser = argparse.ArgumentParser(description="Script for the acquisition of an APTS parameters scan, necessary to find the most suitable combination of parameters that will be used as the operating point")
parser.add_argument('--serial' ,'-s',help='serial number of the DAQ board')
parser.add_argument('proximity',metavar="PROXIMITY",help='Proximity card name (e.g. APTS-003). The name must be in the same format as the corresponding calibration file.')
parser.add_argument('--ntrg'   ,'-n',type=int,help='number of triggers',default=1000)
parser.add_argument('--trg_type','-ty',default=1, help='trigger: ext, int',type=lambda t: {'ext':0,'int':1}[t])
parser.add_argument('--trg_thr','-tt',type=int,help='auto trigger threshold',default=20)
parser.add_argument('--n_frames_before','--n-frames-before','-nfb', default=10, type=int, help='Number of frame before trigger/signal 1-100')
parser.add_argument('--n_frames_after','--n-frames-after','-nfa', default=40, type=int, help='Number of frame after trigger/signal 1-700')
parser.add_argument('--sampling_period','--sampling-period','-sp',default=40, type=int, help='Sampling period 1-40 (unit of 6.25 ns)')
parser.add_argument('--pulse','-p',default=None,help='PULSE: s(first pixel), out(outer), in(inner), f(full)',type=lambda t: {'s':0,'out':1,'in':2,'f':3}[t] )
parser.add_argument('--vh','-v',     type=float,help='VH DAC setting in mV')
parser.add_argument('--ibn_range','-ribn', nargs=3, type=int, default= [200, 1200, 200], help='Range of IBIASN (ex.: min max step).')
parser.add_argument('--ibp_range','-ribp', nargs=3, type=int, default= [20, 140, 30], help='Range of IBIASP (ex.: min max step).')
parser.add_argument('--ires_range','-rires', nargs=3, type=float, default= [0.1, 1, 0.45], help='Range of IRESET (ex.: min max step).')
parser.add_argument('--ib3_range','-rib3', nargs=3, type=int, default= [200, 1200, 200], help='Range of IBIAS3 (ex.: min max step).')
parser.add_argument('--ib4_range','-rib4', nargs=3, type=int, default= [1500, 7500, 1500], help='Range of IBIAS4 (ex.: min max step).')
parser.add_argument('--vres_range','-rvres', nargs=3, type=int, default= [20, 900, 20], help='Range of VRESET (ex.: min max step).')
parser.add_argument('--prefix',default='apts_',help='Output file prefix')
parser.add_argument('--suffix',default='',help='Output file suffix')
parser.add_argument('--output-dir','-o',default=default_data_dir,help='Directory for output files.')
parser.add_argument('--vbbdir','-vdir',default='vbb_0',help='Directory for vbb folders.')
args = parser.parse_args()

now = datetime.datetime.now()

ibn_range = make_range(args.ibn_range) 
ibp_range = make_range(args.ibp_range) 
ires_range = make_range(args.ires_range)
ib3_range = make_range(args.ib3_range) 
ib4_range = make_range(args.ib4_range) 
vres_range = make_range(args.vres_range) 

ires_old=0 #variable used to keep track of the IRESET setting

try:
    daq = APTSDAQBoard(serial=args.serial, calibration=args.proximity)
    if args.vh is not None: daq.set_vdac('CE_VOFFSET_AP_DP_VH', args.vh)
    if args.pulse!=None: daq.set_pulse_sel(sel0=(args.pulse&1),sel1=((args.pulse>>1)&1))

    for ires in ires_range:
        for ibn in ibn_range:
            for ibp in ibp_range:
                for ib3 in ib3_range:
                    for ib4 in ib4_range:
                        folder_dir = f"ires_{ires}/ibn_{int(ibn)}/ibp_{int(ibp)}/ib3_{int(ib3)}/ib4_{int(ib4)}/vbb_{args.vbbdir}" # organizes everything in folders, one for each step of each parameter
                        directory = os.path.join(default_data_dir, folder_dir)
                        os.makedirs(directory, exist_ok=True) #create the directory if it does not exist
                        for vres in vres_range:
                            
                            if args.serial:
                                fname = f"{args.prefix}{args.serial}_{now.strftime('%Y%m%d_%H%M%S')}_ires{ires}_ibn{int(ibn)}_ibp{int(ibp)}_ib3{int(ib3)}_ib4{int(ib4)}_vres{int(vres)}{args.suffix}"
                            else:
                                fname = f"{args.prefix}{now.strftime('%Y%m%d_%H%M%S')}_ires{ires}_ibn{int(ibn)}_ibp{int(ibp)}_ib3{int(ib3)}_ib4{int(ib4)}_vres{int(vres)}{args.suffix}"

                            logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                               filename=os.path.join(directory,fname+".log"),filemode='w', force=True)
                            log_term = logging.StreamHandler()
                            log_term.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
                            log_term.setLevel(logging.INFO)
                            logging.getLogger().addHandler(log_term)

                            daq.set_idac('CE_COL_AP_IBIASN', ibn)
                            daq.set_idac('AP_IBIASP_DP_IDB', ibp)
                            daq.set_idac('CE_PMOS_AP_DP_IRESET', ires)
                            daq.set_idac('AP_IBIAS3_DP_IBIAS', ib3)
                            daq.set_idac('CE_MAT_AP_IBIAS4SF_DP_IBIASF', ib4)
                            daq.set_vdac('AP_VRESET', vres)


                            if ires==ires_old:
                                sleep(0.4)
                                print('Waiting 0.4s for the settings of the parameters')
                            else:
                                sleep(9)
                                print('Waiting 9s for the setting of IRESET')
                            ires_old = ires

                            daq.configure_readout(trg_type=args.trg_type,trg_thr=args.trg_thr,pulse=(args.pulse!=None),n_frames_before=args.n_frames_before, n_frames_after=args.n_frames_after,sampling_period=args.sampling_period)
                            sleep(1) # wait for baseline to settle after switching on the ADC
                            logging.info('Starting readout')
                            with open(os.path.join(directory,fname+".raw"),'wb') as outfile:
                                for itrg in tqdm(range(args.ntrg),desc='Trigger'):
                                    data=daq.read_event()
                                    assert data is not None
                                    outfile.write(data)
                            logging.info('Done')
                            print(f'{fname} created')

except KeyboardInterrupt:
    logging.info('User stopped.')
except Exception as e:
    logging.exception(e)
    logging.fatal('Terminating!')
