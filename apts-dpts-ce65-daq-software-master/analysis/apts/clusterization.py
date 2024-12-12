#!/usr/bin/env python3

import numpy as np
import matplotlib.pyplot as plt
from sys import getsizeof as size
import matplotlib
import argparse
import os
import sys
import re 
from scipy.optimize import curve_fit
import signal_extraction
import json
import constants
import pathlib

def clusterization(args):
    """ clusterization takes args, and a dictionary with baseline, rms, p2p, data_base, signal
    and returns an other dictionary with cluster variables: seed, seed_index, matrix, cluster_size"""
        
    print('Started clusterization...')

    file_name = str(pathlib.PurePosixPath(args.file_in).stem)
    
    path = args.directory
    if not os.path.exists(path):
        os.makedirs(path)
        
    #input_dictionary = signal_extraction(args)
    signal_extraction_dictionary = 'return_dictionary' + '_' + file_name + '.npz'
    input_dictionary = np.load(os.path.join(args.directory, signal_extraction_dictionary))

    signal = input_dictionary['signal']
    nEvent = signal.shape[0]
    p2p = input_dictionary['p2p']
    noise = input_dictionary['noise']
    baseline = input_dictionary['baseline']

    seed = np.zeros((nEvent))

    seed_index = np.zeros((nEvent,1,1))
   
    #Reshaping for finding amx pixels
    signal_reshaped = signal.reshape(signal.shape[0],signal.shape[1]*signal.shape[2])
    locs = np.argmax(signal_reshaped,axis = 1)
    seed_index = np.array(list(zip(locs//signal.shape[2],locs%signal.shape[1])))
    
    if args.threshold_kind == 'mv':
        threshold = args.threshold_value
    else:
        with open(os.path.join(args.directory,'Analysis/results_'+file_name+'.json'), 'r') as file_json:
            data_json = json.load(file_json)
        seed_fit = data_json['seed_1640']
        threshold = args.threshold_value*seed_fit/constants.EL_5_9_KEV

    matrix = np.zeros((nEvent))
    cluster_size = np.zeros((nEvent))
    
    neighbours_sig = np.zeros((nEvent))
    
    for ev in range(0,nEvent):
        if (seed_index[ev,0]  == 1 or seed_index[ev,0] ==2)  and (seed_index[ev,1] == 1 or seed_index[ev,1] ==2):
            if np.max(signal[ev,1:3,1:3])> threshold:
                matrix[ev] = np.sum(signal[ev,seed_index[ev,0]-1:seed_index[ev,0]+2,seed_index[ev,1]-1:seed_index[ev,1]+2])
                seed[ev] = np.max(signal[ev,1:3,1:3])
            else:
                seed[ev] = np.nan
                matrix[ev] = np.nan
            for row in range(0,4):
                for column in range(0,4):
                    if signal[ev, row ,column]> threshold:
                        if (((seed_index[ev,0] - row) == 0 and abs(seed_index[ev,1] - column)<=1) or
                            (abs(seed_index[ev,0] - row) <= 1 and (seed_index[ev,1] - column)==0) or
                            (abs(seed_index[ev,0] - row) == 1 and abs(seed_index[ev,1] - column)==1 and (signal[ev, row ,seed_index[ev,1]]>threshold or signal[ev, seed_index[ev,0] ,column]>threshold))):
                            cluster_size[ev] = cluster_size[ev]+1
                        
                    if (seed_index[ev,0] - row) != 0 or (seed_index[ev,1] - column)!=0:
                        neighbours_sig[ev] += signal[ev,row,column]

        else:
            cluster_size[ev] = None
            matrix[ev] = None
            neighbours_sig[ev] = np.nan
            seed[ev] = np.nan
    
    return_values = ['seed', 'seed_index', 'matrix', 'cluster_size', 'neighbours_sig','threshold','noise','baseline']
    return_arrays = [seed, seed_index, matrix, cluster_size, neighbours_sig,threshold, noise, baseline]
    return_dict_cluster = dict(zip(return_values, return_arrays))
     # save dictionary to .npz file
    cluster_dictionary = 'return_dict_cluster' + '_' + file_name
    np.savez(os.path.join(path, cluster_dictionary), **return_dict_cluster)
    return return_dict_cluster
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APTS signal extraction")
    parser.add_argument('file_in',metavar="file_in", help='Directory and file name with extension for the input file (e.g. apts_20220422_102553.npy) ')
    parser.add_argument('--directory','-d',default = '.',help = 'Directory for input files.')
    parser.add_argument('--threshold_kind','-thrk',default='mv',type=str.lower, help='Threshold: mv, el. Kind of threshold to apply (in mV or electrons). Default %(default)s. CAVEAT: electron threshold can be used only if already run the analysis once.',choices=['mv','el'])
    parser.add_argument('--threshold_value','-thrv', type=float,help='Choose the threshold to discharge the noise. Default =  %(default)s.',default = 10)
    parser.add_argument('--beam_test', '-bt', action = 'store_true',help='Select if you want to analyse beam test data')
    args = parser.parse_args()
    
    clusterization(args)
