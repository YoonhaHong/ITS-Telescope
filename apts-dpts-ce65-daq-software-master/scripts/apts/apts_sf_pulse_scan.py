#!/usr/bin/env python3

import numpy as np
import sys,os
import datetime
import argparse
import time
sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__),"../../apts")))
import apts_helpers
import mlr1daqboard

import pathlib

from time import sleep

from labequipment import HAMEG

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Script for extract APTS pulsed event',formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    parser.add_argument('--volt','-v',action='store_true',default=False,help='Optionally plot the pulse in volts instead of ADC. This uses 1 ADC unit = 38 uA.')
    parser.add_argument('--vbb_channel','-vc',type=int,default=2,help='Set Vbb(Back-bias Voltage) channel')
    parser.add_argument('--daq_channel','-dc',type=int,default=1,help='Set DAQ voltage channel')
    parser.add_argument('--vbb','-vbb', type=float, default=0, help='Set Vbb(Back-bias Voltage) for pulsing using HAMEG')
    parser.add_argument('--prefix',default=pathlib.Path(sys.argv[0]).stem,help='Output file prefix')
    parser.add_argument('--ntrg','-n',default=1000,type=int,help='Set the number of trigger')
    parser.add_argument('--hameg_path','-hpath',default='/dev/serial/by-id/usb-HAMEG_HAMEG_HO720_100030280926-if00-port0',type=str,help='HAMEG path')
    
    apts_helpers.add_common_args(parser)
    args=parser.parse_args()

    # Get now time
    now=datetime.datetime.now()

    # Control a HAMEG remotely
    hmg = HAMEG(args.hameg_path)
    hmg.set_volt(args.vbb_channel,args.vbb)
    hmg.set_volt(args.daq_channel,5)
    hmg.power(True,args.vbb_channel)
    hmg.power(True,args.daq_channel)

    # Check if the APTS turn on or not
    apts = mlr1daqboard.APTSDAQBoard(serial=args.serial,calibration=args.proximity)
    if apts.is_chip_powered()==False:
        print("APTS was off --> turning ON")
        apts.power_on()
    
    # Configure multiplexer
    if args.mux!=-1:
        apts.set_mux(args.mux)
    else:
        print("Not setting multiplexer selection, as args.mux = " + str(args.mux))

    # Set reset currents
    nfb=args.n_frames_before
    apts.set_pulse_sel(sel0=(args.pulse&1),sel1=((args.pulse>>1)&1))
    apts.configure_readout(pulse=True, n_frames_before=nfb,n_frames_after=args.n_frames_after,sampling_period=args.sampling_period)
    apts.set_vdac('CE_VOFFSET_AP_DP_VH',args.vh)
    apts.set_idac('CE_PMOS_AP_DP_IRESET',args.ireset)
    apts.set_idac('CE_COL_AP_IBIASN',args.ibiasn)
    apts.set_idac('AP_IBIASP_DP_IDB',args.ibiasp)
    apts.set_idac('AP_IBIAS3_DP_IBIAS',args.ibias3)
    apts.set_vdac('AP_VRESET',args.vreset)
    apts.set_idac('CE_MAT_AP_IBIAS4SF_DP_IBIASF',args.ibias4)
    for _ in range(args.expert_wait):
        sleep(1)

    time.sleep(1)

    dac_data_list = list()
    
    for i in range(0,args.ntrg):
        data,ts = apts.read_event(format=False)
        dac_data = mlr1daqboard.decode_apts_event(data).T
        dac_data_list.append(dac_data)
    
    fname = f"{args.chip_ID}_Vbb{args.vbb}_{now.strftime('%Y%m%d_%H%M%S')}{args.suffix}"
    return_name = ['pulsing_all','chip_ID','vbb','vh','ireset','ibiasn','ibiasp','ibias3','vreset','ibias4']
    return_array = [dac_data_list,args.chip_ID,args.vbb,args.vh,args.ireset,args.ibiasn,args.ibiasp,args.ibias3,args.vreset,args.ibias4]
    return_dict = dict(zip(return_name,return_array))
    np.savez(os.path.join(args.output_dir,fname+'.npz'),**return_dict)
