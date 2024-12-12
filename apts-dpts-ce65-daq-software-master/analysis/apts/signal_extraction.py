#!/usr/bin/env python3

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import argparse
import os
import sys
import re
import json
import pathlib

def signal_extraction(args):
    """ signal_extraction takes args
    and returns a dictionary with baseline, rms, p2p, data_centered, signal """
        
    #Load the file and extract infos: name, voltage, number of events, number of frames
    if args.no_calib == 0:
        data_array = np.load(os.path.join(args.directory, str(pathlib.PurePosixPath(args.file_in).stem)  + '_calibrated.npy'))
    else:
        data_array = np.load(str(pathlib.PurePosixPath(args.file_in).with_suffix('.npy')))
    n_events = data_array.shape[0]
    #n_events = 10000
    n_frame = data_array.shape[3]
         
    #JSON file
    with open(str(pathlib.PurePosixPath(args.file_in).with_suffix('.json')), 'r') as file_json:
        data_json = json.load(file_json)
    chip_ID = data_json['chip_ID']
    n_frames_before = data_json['n_frames_before']
    path = args.directory
    if not os.path.exists(path):
        os.makedirs(path)
    assert (n_frames_before + data_json['n_frames_after']) == n_frame, 'Error : number of frames from data different from the one found in json file'
    
    print('Extracting signals from',chip_ID, 'at a voltage of ',data_json['vbb'])
    print(n_events, 'number of events found with a total of ',n_frame, ' frames each extracted from data.' )

    signal = np.zeros((n_events,4,4))
    noise = np.zeros((n_events,4,4))
    
    n_frame_baseline = n_frames_before - 10
    if args.baseline_mean is False:
        baseline = np.mean(data_array[:,:,:,n_frames_before-4:n_frames_before-3],axis = 3)
    else:
        baseline = np.mean(data_array[:,:,:,:n_frame_baseline],axis = 3)
    rms = np.std(data_array[:,:,:,:n_frame_baseline], axis = 3)
    p2p= np.max(data_array[:,:,:,:n_frame_baseline], axis = 3) - np.min(data_array[:,:,:,:n_frame_baseline], axis = 3)
                     
    data_centered = baseline[:,:,:,np.newaxis] - data_array
    
    frame_max = np.zeros((n_events))
    frame_max[:] = np.nan

    frame_noise = np.zeros((n_events))
    frame_noise[:] = np.nan
    start_range = int(args.signal_extraction_range[0])
    stop_range = int(args.signal_extraction_range[1])
    n_start = 0
    n_stop = 1
    for ev in range(n_events):
        extract_frame_max = np.where(data_centered[ev,:,:,start_range:stop_range] == np.max(data_centered[ev,:,:,start_range:stop_range]))
        frame_max[ev] = extract_frame_max[2][0] + start_range
        frame_noise[ev] = 2*(n_frames_before-4) - frame_max[ev]
        #Maximum of the channel as average around the frame of event maximum
        #at the moment implemented in order t modify it but taking yet only the value at 1 frame
        for i in range(n_start,n_stop):
            signal[ev,:,:] += data_centered[ev,:,:,int(frame_max[ev])+i]
            noise[ev,:,:] += data_centered[ev,:,:,int(frame_noise[ev])-i]
        signal[ev,:,:] = signal[ev,:,:]/(n_stop-n_start)
        noise[ev,:,:] = noise[ev,:,:]/(n_stop-n_start)

    return_values = ['baseline', 'rms', 'p2p', 'data_centered', 'signal','frame_max','noise']
    return_arrays = [baseline, rms, p2p, data_centered, signal, frame_max.astype(int), noise]
    return_dictionary = dict(zip(return_values, return_arrays))
    # save dictionary to .npz file
    signal_extraction_dictionary = 'return_dictionary' + '_' + str(pathlib.PurePosixPath(args.file_in).stem)
    np.savez(os.path.join(path, signal_extraction_dictionary), **return_dictionary)
    return return_dictionary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APTS signal extraction")
    parser.add_argument('file_in',metavar="file_in", help='Run name (e.g. apts_20220422_102553)')
    parser.add_argument('--no_calib','-noc',action = 'store_true',help='Select if you want to disable gain calibration (and take as input data NOT calibrated)')
    parser.add_argument('--directory','-d',default = '.',help='Directory for output files.')
    parser.add_argument('--baseline_mean', '-bsm', action = 'store_true',help='Select if you want to use as baseline the mean of 0-(n_frames_before - 10) frames')
    parser.add_argument('--signal_extraction_range', '-ser', nargs='+', type=str,default= [98, 192] , help='Range of frames used for the extraction of the signal. Example: -ser 98 102')
    args = parser.parse_args()
    
    signal_extraction(args)
