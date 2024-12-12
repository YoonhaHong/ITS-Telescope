#!/usr/bin/env python3
import mlr1daqboard
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import time
import argparse
import datetime
import apts_helpers as helpers
import sys,os,re
from time import sleep
import pathlib


parser = argparse.ArgumentParser(description="Simple example script for plotting APTS pulsed event",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--volt', "--volt",'-v', action='store_true', default=False, help='Optionally plot the pulse in volts instead of ADC. This uses 1 ADC unit = 38 uV.')
helpers.add_common_args(parser)
parser.add_argument('--prefix',default=pathlib.Path(sys.argv[0]).stem,help='Output file prefix')
args = parser.parse_args()

now = datetime.datetime.now()

if args.serial:
    args.fname = f"{args.prefix}{args.serial}_{now.strftime('%Y%m%d_%H%M%S')}{args.suffix}"
else:
    args.fname = f"{args.prefix}{now.strftime('%Y%m%d_%H%M%S')}{args.suffix}"

# pulsing 
nfb=args.n_frames_before
time_unit=6.25*args.sampling_period

apts = mlr1daqboard.APTSDAQBoard(serial=args.serial,calibration=args.proximity)
if apts.is_chip_powered()==False:
        print("APTS was off --> turning ON")
        apts.power_on()

# Configure multiplexer 
if args.mux!=-1:
    apts.set_mux(args.mux)
else:
    print("Not setting multiplexer selection, as args.mux = " + str(args.mux))

# Use non-default reset current
apts.set_pulse_sel(sel0=(args.pulse&1),sel1=((args.pulse>>1)&1))
apts.configure_readout(pulse=True, n_frames_before=nfb, n_frames_after=args.n_frames_after,sampling_period=args.sampling_period)
apts.set_vdac('CE_VOFFSET_AP_DP_VH', args.vh)
apts.set_idac('CE_PMOS_AP_DP_IRESET', args.ireset)
apts.set_idac('CE_COL_AP_IBIASN', args.ibiasn)
apts.set_idac('AP_IBIASP_DP_IDB', args.ibiasp)
apts.set_idac('AP_IBIAS3_DP_IBIAS', args.ibias3)
apts.set_vdac('AP_VRESET', args.vreset)

if args.proximity.split('-')[0]=='APTS':
    apts.set_idac('CE_MAT_AP_IBIAS4SF_DP_IBIASF', args.ibias4)
elif args.proximity.split('-')[0]=='OPAMP':
    apts.set_idac('AP_IBIAS4OPA_DP_IBIASN',       args.ibias4)
    apts.set_vdac('AP_VCASP_MUX0_DP_VCASB',       args.vcasp)
    apts.set_vdac('AP_VCASN_MUX1_DP_VCASN',       args.vcasn)
for _ in range(args.expert_wait):
    sleep(1)


time.sleep(1)

data,ts = apts.read_event(format=False)
dec_data = mlr1daqboard.decode_apts_event(data, mux=True if args.mux in range(4) else False).T
dec_ts =   mlr1daqboard.decode_trigger_timestamp(ts)

if  args.pulse==3:
    title_str = 'Pulsing Full Matrix'
    mat_cor = [0]
elif args.pulse==2:
    title_str = 'Pulsing Inner Corners'
    mat_cor = [8,9,14,10]
elif      args.pulse==1:
    title_str = 'Pulsing Outer Corners'
    mat_cor=[2,0,11,3]
elif  args.pulse==0:
    title_str = 'Pulsing Single Pixel'
    mat_cor = [0]
title_str += ' ' + args.chip_ID
    
fig , (ax1,ax2)= plt.subplots(1,2,num='Event plot',figsize=(15,5))

if args.volt:
    matrix = 38e-3*(np.min(dec_data[:,:]-np.mean(dec_data[0:nfb,:], axis=0), axis=0))
else:
    matrix = np.min(dec_data[:,:]-np.mean(dec_data[0:nfb,:], axis=0), axis=0)

mat = ax1.matshow(matrix.reshape(4,4),cmap=matplotlib.cm.inferno_r)
cbar = fig.colorbar(mat,ax=ax1)
if args.volt:
    cbar.set_label("Amplitude (mV, not gain corrected)")
else:
    cbar.set_label("Amplitude (ADC)")

ax1.set_title(title_str)
ax1.set_xlabel('Column')
ax1.set_ylabel('Row')

cmap=matplotlib.cm.inferno

dec_data = dec_data.reshape(dec_data.shape[0],16)
print("Pixel","Minimum(ADC)","p2p(ADC)","rms(ADC)", "baseline(ADC)")

mapping = mlr1daqboard.APTS_MUX_PIXEL_ADC_MAPPING if args.mux in range(4) else mlr1daqboard.APTS_PIXEL_ADC_MAPPING
for p in range(16):
    if mat_cor and (mapping[p] in mat_cor): 
        w,s = 3.0 ,'-'
    else:
        w,s = 1.5 , '--'
    color = cmap(p/16)
    if args.volt:
        ax2.plot(38e-3*(dec_data[:,p]-np.mean(dec_data[0:nfb,p])),s,lw=w,c=color,label=str(p))
    else:
        ax2.plot(dec_data[:,p]-np.mean(dec_data[0:nfb,p]),s,lw=w,c=color,label=str(p))
    print(p,min(dec_data[:,p]-np.mean(dec_data[0:nfb,p])), (max(dec_data[0:nfb,p])-min(dec_data[0:nfb,p])),np.std(dec_data[0:nfb,p]),np.mean(dec_data[0:nfb,p]))
ax2.legend(ncol=4)
ax2.set_title('Pixels Signals ' + args.chip_ID)
ax2.set_xlabel('Frame Number')
if args.volt:
    ax2.set_ylabel('Amplitude (mV, not gain corrected)')
else:
    ax2.set_ylabel('Amplitude (ADC)')

ax2.grid()

plt.tight_layout()
filename = os.path.join(args.output_dir,args.fname+".png")
plt.savefig(filename, bbox_inches="tight")
plt.show()
