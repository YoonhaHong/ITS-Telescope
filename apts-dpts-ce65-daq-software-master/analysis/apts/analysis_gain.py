#!/usr/bin/env python3

import mlr1daqboard
import logging
import argparse
import os
import re
from time import sleep
import json
from scipy.interpolate import interp1d
import sys
sys.path.append('../../apts/')
from apts_decode import raw_to_npy
import numpy as np
import matplotlib.pyplot as plt

def der(y,x):
    ''' Takes two arrays and returns the numerical derivative as a slope calculated considering the 5 points before and after each point'''
    dy = [0.0]*len(x)
    dy[0] = (y[0] - y[1])/(x[0] - x[1])
    for i in np.arange(1,len(y)-1):
        num = 0
        den = 0
        if i<5: 
            npoints = i
        elif i>=len(y)-5:
            npoints = len(y)-i-1
        else:
            npoints = 5
        for n in range(npoints):
            num+= y[i-(n+1)] - y[i+(n+1)]
            den+= x[i-(n+1)] - x[i+(n+1)]
        dy[i] = num/den
    dy[-1] = (y[-1] - y[-2])/(x[-1] - x[-2])
    return dy

def list_files(dir): # function used to list all the files present inside all the subdirecotries of a directory (given in input)
    r = []
    for subdir,_,files in os.walk(dir):
        for file in files:
            if not (file.endswith('.raw') and (file.startswith('apts_gain') or file.startswith('opamp_gain'))): continue
            r.append(os.path.join(subdir, file))
    return r

def analysis_gain(args):
    for file in list_files(args.file_calibration_directory):
        mux = False
        with open(file.replace('.raw','.json'), 'r') as j:
            data_json = json.load(j)
            if 'chip_ID' in data_json:
                chip_ID = data_json['chip_ID']
                extract_name_volt = re.match(r"[E]?[R]?[1]?A[AF]([12]?[05]?)([BP])?([M])?_(W\d{2})(B\d{1})", chip_ID)
                mux = True if extract_name_volt.group(3)=="M" else False
        mapping = mlr1daqboard.APTS_MUX_PIXEL_ADC_MAPPING if mux else mlr1daqboard.APTS_PIXEL_ADC_MAPPING
        raw_to_npy(file, file.replace('.raw','_decoded.npy'),mux)
        waveforms = np.load(file.replace('.raw','_decoded.npy'))
        k = 0
        baseline_all = []
        vres_range = np.arange(20, 901, 10)
        for ivr in range(len(vres_range)):
            baseline = []
            for i in range(4):
                for j in range(4):
                    baseline.append(np.mean(waveforms[k:k+data_json['ntrg_vres']-1,i,j,:]))
            baseline_all.append(baseline)
            k += data_json['ntrg_vres']
        baseline_all = np.array(baseline_all)
        np.savez(file.replace('.raw','_analysed.npz'), vres_range=vres_range, baseline_all=baseline_all.T)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10,5))
        x_lin = np.linspace(20, 900, num=40)

        for k in range(16):
            ax1.plot(vres_range, 0.0381*baseline_all.T[k, :], linestyle=' ',marker='v', markersize=1)
            y_der = [float(item) for item in der(baseline_all.T[k, :],vres_range)]
            interp = interp1d(vres_range,y_der,kind='cubic', fill_value="extrapolate")
            ax2.plot(x_lin, 0.0381*interp(x_lin), linestyle='-', linewidth=1, label=mapping[k])
            ax2.legend(fontsize='x-small', ncol=3)
        ax1.set_title('Baseline vs V_RESET')
        ax1.set_xlabel(r'V_RESET [mV]')
        ax1.set_ylabel(r'Baseline [mV]')
        ax1.grid(alpha=0.3)
        ax2.set_title('Derivative vs V_RESET')
        ax2.set_xlabel(r'V_RESET [mV]')
        ax2.set_ylabel(r'Derivative')
        ax2.set_xlim([0, 910])
        ax2.set_ylim([0, 0.7])
        ax2.grid(alpha=0.3)
        fig.savefig(file.replace('.raw','_control_plot.pdf'))

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="APTS analysis for gain evaluation")
    parser.add_argument('file_calibration_directory', help='Directory for input files from apts_gain.py output.')
    args = parser.parse_args()

    try:
        analysis_gain(args)
    except KeyboardInterrupt:
        logging.info('User stopped.')
    except Exception as e:
        logging.exception(e)
        logging.fatal('Terminating!')

