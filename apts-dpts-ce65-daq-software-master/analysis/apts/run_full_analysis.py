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
import signal_calibration
import signal_extraction
import clusterization
import data_quality
import analysis
import json

def run_all_1run(args):
    if not (args.no_calib or args.skip_calib):
        signal_calibration.signal_calibration(args)
    signal_extraction.signal_extraction(args)
    clusterization.clusterization(args)
    data_quality.data_quality_noise(args)
    if not args.pulse:
        data_quality.data_quality_frames_hits(args)
    data_quality.data_quality_signals(args)
    analysis.analysis(args)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run all the scripts for source analysis")
    parser.add_argument('file_in',metavar="file_in", help='Directory and file name with extension for the input file (e.g. apts_20220422_102553.npy) ')
    parser.add_argument('directory',help='Directory for output files.')
    parser.add_argument('--file_calibration',help='Directory and file name with extension for the input file used for calibration in npz format (e.g. apts_gain_20220513_182805.npz). Mandatory argument if options --no_calib or --skip_calib not selected.')
    parser.add_argument('--no_calib','-noc',action = 'store_true',help='Select if you want to disable gain calibration (and take as input data NOT calibrated)')
    parser.add_argument('--skip_calib','-skc',action = 'store_true',help='Select if you already performed the gain calibration and to save time you want to skip that step (use as input calibrated data).')
    parser.add_argument('--safe_calib',action = 'store_true',help='Select to use a safer (but slightly less accurate) calibration procedure, robust to the jump in the gain curve observed after irradiation.')
    parser.add_argument('--threshold_kind','-thrk',default='mv',type=str.lower, help='Threshold: mv, el. Kind of threshold to apply (in mV or electrons). Default %(default)s. CAVEAT: electron threshold can be used only if already run the analysis once.',choices=['mv','el'])
    parser.add_argument('--threshold_value','-thrv', type=float,help='Choose the threshold to discharge the noise. Default =  %(default)s.',default = 10)
    parser.add_argument('--cmin',default = 1, type=float, help='For the 2d hist of neighbour - seed: all bins that has count less than cmin will not be displayed (Default: cmin = 1).')
    parser.add_argument('--cmax',default = 800, type=float, help='For the 2d hist of neighbour - seed: all bins that has count more than cmax will not be displayed (Default: cmax = 800).')
    parser.add_argument('--frame_range_min','-frm', default = None, type=int, help='Select the minimum frame for the Frames_apts...pdf plot, from 0 to number of frames. (default n_frames_before - 10)')
    parser.add_argument('--frame_range_max','-frM', default = None, type=int, help='Select the maximum frame for the Frames_apts...pdf plot, from 0 to number of frames. (default n_frames_before + 10)')
    parser.add_argument('--ev_sel', '-evs',default = 5, type = int, help='Select a single event and pixel map you want to see (plot Signal_X_apts_Y.pdf), from 0 to the total number of entries (default = 5)')
    parser.add_argument('--events_min', '-evm',default = 0, type=int, help='Select the first event to plot (default = 0) (for plot ev_xx_signals_yy.pdf).')
    parser.add_argument('--events_max', '-evM',default = 10, type=int, help='Select the last event to plot (default = 10) (for plot ev_xx_signals_yy.pdf).')
    parser.add_argument('--ext_trg_signals', '-extrg', action = 'store_true',help='Select if you want to see some signals which is not noise. If true, it will ignore the events selections (ev_sel, events_min, events_max).')
    parser.add_argument('--linear_scale', '-ls',action = 'store_true',help='Select if you want to plot the signal plots with linear scale (Default log scale)')
    parser.add_argument('--number_of_bins','-nob',type = int, default = 200,help='Number of bins for plots of signal distribution. Default 200.')
    parser.add_argument('--baseline_mean', '-bsm', action = 'store_true',help='Select if you want to use as baseline the mean of 0-(n_frames_before - 10) frames')
    parser.add_argument('--rms_p2p', action = 'store_true', help='Select if you want to plot rms and p2p distributions')
    parser.add_argument('--signal_extraction_range', '-ser', nargs='+', type=str,default= [98, 192] , help='Range of frames used for the extraction of the signal. Example: -ser 98 102')
    parser.add_argument('--beam_test', '-bt', action = 'store_true',help='Select if you want to analyse beam test data')
    parser.add_argument('--no_fit', '-nof', action = 'store_true',help='Select if you do not want to fit the spectra')
    parser.add_argument('--pulse', '-pulse', action = 'store_true',help='Select if you do not want to analyse pulsing data')


    args = parser.parse_args()

    run_all_1run(args)
