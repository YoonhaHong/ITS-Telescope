#!/usr/bin/env python3

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import argparse
import os
import sys
import re
from scipy.interpolate import interp1d
import pathlib

def signal_calibration(args):
    """ calibration takes args
    and returns a calibrated data """
    print('Started calibration ...') 
    #Load the file and extract infos: name, voltage, number of events, number of frames
    data_array = np.load(str(pathlib.PurePosixPath(args.file_in).with_suffix('.npy')))
    n_events = data_array.shape[0]
    n_frame = data_array.shape[3]
    
    data_calibration = np.load(args.file_calibration)
    input = data_calibration['vres_range']
    output = data_calibration['baseline_all']
    
    data_array_calibrated = np.zeros((n_events,4,4,n_frame))
    
    n = 0
    for row in range(4):
        for column in range(4):
            if args.safe_calib:
                #filter the calibration data in order to make it monotonic and avoid interpolation issues
                gain_in = []
                gain_out = []
                v = np.inf
                for i in range(len(input)-1,-1,-1):
                    if output[n,i]<v:
                        v = output[n,i]
                        gain_in = [input[i]] + gain_in
                        gain_out = [output[n,i]] + gain_out
                interp = interp1d(gain_out,gain_in,kind='linear', fill_value="extrapolate") #use safe linear interpolation, cubic can cause problems
            else :
                interp = interp1d(output[n,:],input,kind='cubic', fill_value="extrapolate")
            n += 1
            data_array_calibrated[:, row, column, :] = interp(data_array[:, row, column, :])
            
    if not os.path.exists(args.directory):
        os.makedirs(args.directory)
    np.save(os.path.join(args.directory, str(pathlib.PurePosixPath(args.file_in).stem) + "_calibrated.npy"), data_array_calibrated)
         
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APTS signal extraction")
    parser.add_argument('file_in',metavar="file_in", help='Directory and file name with extension for the input file (e.g. apts_20220422_102553.npy) ')
    parser.add_argument('file_calibration',metavar="file_calibration", help='Directory and file name with extension for the input file used for calibration in npz format (e.g. apts_gain_20220513_182805.npz) ')
    parser.add_argument('--directory','-d',default = '.',help='Directory for output files.')
    parser.add_argument('--safe_calib',action = 'store_true',help='Select to use a safer (but slightly less accurate) calibration procedure, robust to the jump in the gain curve observed after irradiation.')
    args = parser.parse_args()
    
    signal_calibration(args)
