#!/usr/bin/env python3

import numpy as np
import matplotlib.pyplot as plt
from sys import getsizeof as size
import matplotlib
import argparse
import os
import sys
import re
import signal_extraction
import json
import constants
import pathlib

def data_quality_noise(args):
    """ data_quality_noise takes args, and a dictionary with baseline, rms, p2p, data_centered, signal
    and returns plots of noise plots"""
    
    print('Started data quality analysis...')

    dq_path = os.path.join(args.directory, 'Data_Quality')

    if not os.path.exists(dq_path):
        os.makedirs(dq_path)
    
    file_name = str(pathlib.PurePosixPath(args.file_in).stem)
    
    #input_dictionary = signal_extraction(args)
    signal_extraction_dictionary = 'return_dictionary' + '_' + file_name + '.npz'
    input_dictionary = np.load(os.path.join(args.directory, signal_extraction_dictionary))
    
    rms = input_dictionary['rms']
    p2p = input_dictionary['p2p']
    baseline = input_dictionary['baseline']
    noise = input_dictionary['noise']
    
    #input_dict_cluster = clusterization(args)
    cluster_dictionary = 'return_dict_cluster' + '_' + file_name  + '.npz'
    input_dict_cluster = np.load(os.path.join(args.directory, cluster_dictionary))
    
    neighbours_sig =  input_dict_cluster['neighbours_sig']
    seed =  input_dict_cluster['seed']

    max_RMS = 3*np.mean(rms)
    max_p2p = 3*np.mean(p2p)

    min_base = np.min(baseline)
    max_base = np.max(baseline)

    min_noise = np.min(noise)
    max_noise = np.max(noise)

    seed_limit = 150
    seed_label = 'mV'
    if args.no_calib:
        seed_limit = 3000
        seed_label = 'ADC'
    
    c = iter(matplotlib.cm.rainbow(np.linspace(0,1,16)))
    if args.rms_p2p:
        fig_rms_p2p, ax_rms_p2p = plt.subplots(1,3,num='RMS',figsize=(15,5))
        for row in range(0,4):
            for column in range(0,4):
                color = next(c)
                ax_rms_p2p[0].hist(rms[:,row,column], bins = np.arange(0, max_RMS + (max_RMS-0)/80, (max_RMS-0)/80), color = color,label = f"[{row}][{column}]",alpha=.2, density = True)
                ax_rms_p2p[1].hist(p2p[:,row,column], bins = np.arange(0, max_p2p + (max_p2p-0)/50, (max_p2p-0)/50), color = color,label = f"[{row}][{column}]",alpha=.2, density = True)
                ax_rms_p2p[2].hist(baseline[:,row,column], bins = np.arange(min_base, max_base + (max_base-min_base)/50, (max_base-min_base)/50) , color = color,label = f"[{row}][{column}]",alpha=.2, density = True)
        ax_rms_p2p[0].set(xlabel=f'Baseline RMS ({seed_label})',
            ylabel='Relative frequency',
            title='rms',
            xlim=([0, max_RMS]))

        ax_rms_p2p[1].set(xlabel=f'Baseline peak-to-peak ({seed_label})',
            ylabel='Relative frequency',
            title='p2p',
            xlim=([0, max_p2p]))

        ax_rms_p2p[2].set(xlabel=f'Baseline ({seed_label})',
            ylabel='Relative frequency',
            title='baseline')
        ax_rms_p2p[2].legend(bbox_to_anchor=(1.05, 0.95))

        fig_rms_p2p.tight_layout()
        fig_rms_p2p.savefig(os.path.join(dq_path,'RMS_p2p'+ '_' + file_name + '.pdf'))

    c = iter(matplotlib.cm.rainbow(np.linspace(0,1,16)))
    fig_noise, ax_noise = plt.subplots(1,2,num='Noise',figsize=(12,5))
    for row in range(0,4):
        for column in range(0,4):
            color = next(c)
            ax_noise[0].hist(noise[:,row,column], bins = np.arange(min_noise, max_noise + (max_noise-min_noise)/50, (max_noise-min_noise)/50), color = color,label = f"RMS = {round(np.std(noise[:,row,column], axis=0),2)} {seed_label}",alpha=.2, density = True)
            ax_noise[1].hist(baseline[:,row,column], bins = np.arange(min_base, max_base + (max_base-min_base)/50, (max_base-min_base)/50) , color = color,label = f"[{row}][{column}]",alpha=.2, density = True)

    ax_noise[0].set(xlabel=f'Noise ({seed_label})',
        ylabel='Relative frequency',
        title='Noise')
    ax_noise[0].legend(bbox_to_anchor=(0.85, 0.95))

    ax_noise[1].set(xlabel=f'Baseline ({seed_label})',
        ylabel='Relative frequency',
        title='baseline')
    ax_noise[1].legend(bbox_to_anchor=(1.05, 0.95))
    
    fig_noise.tight_layout()
    fig_noise.savefig(os.path.join(dq_path,'Noise'+ '_' + file_name + '.pdf'))
    
    if not args.pulse:
        fig_seed_neigh, ax_seed_neigh = plt.subplots(sharex = False, sharey = False, figsize=(7,5))
        mat = ax_seed_neigh.hist2d(seed[:],neighbours_sig[:], bins = (50,50), cmin = args.cmin, cmax = args.cmax,cmap = matplotlib.cm.viridis, range=[[0, seed_limit],[-int(seed_limit/6), seed_limit]], norm = matplotlib.colors.LogNorm())

        fig_seed_neigh.colorbar(mat[3],ax=ax_seed_neigh, extend='min')
        ax_seed_neigh.set(
                xlabel=f'Seed pixel signal ({seed_label}) ',
                ylabel=f'Sum of neighbours signals ({seed_label})')
        fig_seed_neigh.tight_layout()
        ax_seed_neigh.text(0.75, 0.98, f"Seed threshold = {args.threshold_value} {seed_label}", fontsize=7, transform=ax_seed_neigh.transAxes)
        #fig_seed_neigh.savefig(os.path.join(path,'Neighbours_seed.pdf'))
        fig_seed_neigh.savefig(os.path.join(dq_path,'Neighbours_seed'+ '_' + file_name + '.pdf'))


def data_quality_frames_hits(args):
    """ data_quality_frames_hits takes args, and a dictionary with baseline, rms, p2p, data_centered, signal
    and returns a plot with frames distribution and hitmap plots, both of total number of hits and of seed"""

    #JSON file
    with open(str(pathlib.PurePosixPath(args.file_in).with_suffix('.json')), 'r') as file_json:
        data_json = json.load(file_json)
    n_frames_before = data_json['n_frames_before']
    n_frames_after = data_json['n_frames_after']
    dq_path = os.path.join(args.directory, 'Data_Quality')

    if not os.path.exists(dq_path):
        os.makedirs(dq_path)
    
    file_name = str(pathlib.PurePosixPath(args.file_in).stem)
    
    #input_dictionary = signal_extraction(args)
    signal_extraction_dictionary = 'return_dictionary' + '_' + file_name + '.npz'
    input_dictionary = np.load(os.path.join(args.directory, signal_extraction_dictionary))

    rms = input_dictionary['rms']
    p2p = input_dictionary['p2p']
    data_centered = input_dictionary['data_centered']
    signal = input_dictionary['signal']
    frame_max = input_dictionary['frame_max']

    hit_frequency = np.zeros((4,4))
    hit_frequency_max = np.zeros((4,4))
    n_events = data_centered.shape[0]
    #n_events = 100

    n_frame = data_centered.shape[3]
    count_ev_frame = np.zeros((n_events,4,4))
    count_ev_frameMax = np.zeros((n_events,4,4))
    count_ev_frame[:,:,:] = count_ev_frameMax[:,:,:] = np.nan

    seed_label = 'mV'
    if args.no_calib:
        seed_label = 'ADC'
        
    if args.threshold_kind == 'mv':
        threshold = args.threshold_value
    else:
        with open(os.path.join(args.directory,'Analysis/results_'+ file_name +'.json'), 'r') as file_json:
            data_json = json.load(file_json)
        seed_fit = data_json['seed_1640']
        threshold = args.threshold_value*seed_fit/constants.EL_5_9_KEV

    count_difference_frame_max = np.zeros((n_events,4,4))
    count_difference_frame_max[:] = np.nan

    frame_max_pixel = np.zeros((n_events))
    frame_max_pixel[:] = np.nan
    
    if args.frame_range_min == None:
        fig_fr_min = n_frames_before-10
    else:
        fig_fr_min = args.frame_range_min
    if args.frame_range_max == None:
        fig_fr_max = n_frames_before+10
    else:
        fig_fr_max = args.frame_range_max
    fig_fr_diff_min = -2
    fig_fr_diff_max = 5
    
    ev_out_range_fmc = 0
    ev_out_range_fme = 0
    ev_out_range_ffm = 0
    index_double_ev = 0

    for ev in range(n_events):
        ev_index=0
        for row in range(4):
            for column in range(4):
                if np.max(data_centered[ev,row,column,:]) > threshold:
                    hit_frequency[row,column] +=1
                    if data_centered[ev,row,column,frame_max[ev]] == np.max(data_centered[ev,:,:,frame_max[ev]]):
                        ev_index+=1
                        if ev_index>1: 
                            index_double_ev+=1
                            continue
                        count_ev_frameMax[ev,row,column] = frame_max[ev]
                        hit_frequency_max[row,column]+=1
                        if count_ev_frameMax[ev,row,column] < fig_fr_min or count_ev_frameMax[ev,row,column] >= fig_fr_max:
                            ev_out_range_fme += 1
                    extract_frame_max = np.where(data_centered[ev,row,column,:] == np.max(data_centered[ev,row,column,:]))
                    frame_max_pixel[ev] = extract_frame_max[0][0]
                    count_ev_frame[ev,row,column] = int(frame_max_pixel[ev])
                    if data_centered[ev,row,column,int(frame_max_pixel[ev])] != np.max(data_centered[ev,:,:,int(frame_max_pixel[ev])]):
                        count_difference_frame_max[ev,row,column] = int(frame_max_pixel[ev]) - frame_max[ev]
                        if count_difference_frame_max[ev,row,column] < fig_fr_diff_min or count_difference_frame_max[ev,row,column] >= fig_fr_diff_max:
                            ev_out_range_ffm += 1
                    if count_ev_frame[ev,row,column] < fig_fr_min or count_ev_frame[ev,row,column] >= fig_fr_max:
                        ev_out_range_fmc += 1
                   
    fig_fr = plt.figure(figsize=(10,10))
    gs = fig_fr.add_gridspec(4,4,hspace = 0,wspace = 0)
    ax_frame = gs.subplots(sharex = True, sharey = True)
    
    for row in range(4):
        for column in range(4):
            y,x,_ = ax_frame[row,column].hist(count_ev_frame[:,row,column],bins = np.arange(0,n_frames_before+n_frames_after, 1),color = matplotlib.cm.rainbow(0.2), label = f"Max signal frame, (threshold = {int(threshold)} {seed_label})",alpha=.5)
            ye,xe,_ = ax_frame[row,column].hist(count_ev_frameMax[:,row,column],bins = np.arange(0, n_frames_before+n_frames_after, 1),color = matplotlib.cm.rainbow(0.95), label = f"Seed - Max signal frame (threshold = {int(threshold)} {seed_label})",alpha=.5)
            ax_frame[row,column].set(xlabel='Frame ',
                                 ylabel='Entries',
                                 xlim=[fig_fr_min, fig_fr_max])

    for ax in fig_fr.get_axes():
        ax.label_outer()
        ax.set_yscale("log")
        
    fig_fr.suptitle(f'Frame with max signal amplitude of channel or event (seed). Events out of range: {ev_out_range_fmc} (ch),{ev_out_range_fme} (seed). Events with double max found: {index_double_ev}', fontsize=10)
    ax_frame[0,3].legend(loc='upper right')
    fig_fr.tight_layout()
    fig_fr.savefig(os.path.join(dq_path,'Frames'+ '_' + file_name + '.pdf'))
    
    fig_hamp, ax_hamp = plt.subplots(1,2,num='Total hits',figsize=(15,5))
    mat = ax_hamp[0].matshow(hit_frequency,cmap = matplotlib.cm.Blues_r)
    ax_hamp[0].set(xlabel='Column',
                  ylabel='Row',
                  title=f'Hit map (signal > threshold = {int(threshold)} {seed_label})')
    ax_hamp[0].tick_params(top=False, labeltop=False, bottom=True, labelbottom=True)
    cbar = fig_hamp.colorbar(mat,ax = ax_hamp[0])
    cbar.set_label('Frequency', rotation=270, labelpad=15)
    mat1 = ax_hamp[1].matshow(hit_frequency_max,cmap = matplotlib.cm.Blues_r)
    ax_hamp[1].set(xlabel='Column',
                  ylabel='Row',
                  title=f'Seed hit map (seed signal > threshold = {int(threshold)} {seed_label})')
    ax_hamp[1].tick_params(top=False, labeltop=False, bottom=True, labelbottom=True)
    cbar1 = fig_hamp.colorbar(mat1,ax = ax_hamp[1])
    cbar1.set_label('Frequency', rotation=270, labelpad=15)
    fig_hamp.savefig(os.path.join(dq_path,'HitMaps'+ '_' + file_name + '.pdf'))
    
    fig_frame_frame_max = plt.figure(figsize=(10,10))
    gs_diff_frame = fig_frame_frame_max.add_gridspec(4,4,hspace = 0,wspace = 0)
    ax_frame_frame_max = gs_diff_frame.subplots(sharex = True, sharey = True)
    for row in range(4):
        for column in range(4):
            y,x,_ = ax_frame_frame_max[row,column].hist(count_difference_frame_max[:,row,column],bins = np.arange(-100, 100, 1),color = matplotlib.cm.rainbow(0.2),alpha=.5)
            ax_frame_frame_max[row,column].set(xlabel='Channel-Event frame max',
                                 ylabel='Entries',
                                 xlim=[fig_fr_diff_min, fig_fr_diff_max])
    for ax in fig_frame_frame_max.get_axes():
        ax.label_outer()
        ax.set_yscale("log")
    fig_frame_frame_max.suptitle(f'Frame difference among max of the channel and max of the event (seed). Events out of range: {ev_out_range_ffm}')
    fig_frame_frame_max.tight_layout()
    fig_frame_frame_max.savefig(os.path.join(dq_path,'frame_frame_max'+ '_' + file_name + '.pdf'))

def data_quality_signals(args):
    """ data_quality_signals takes args, and a dictionary with baseline, rms, p2p, data_centered, signal
    and returns a plot with a signal event and an other with a selectable number of events"""

    dq_path = os.path.join(args.directory, 'Data_Quality')

    if not os.path.exists(dq_path):
        os.makedirs(dq_path)
    
    file_name = str(pathlib.PurePosixPath(args.file_in).stem)
        
    #input_dictionary = signal_extraction(args)
    signal_extraction_dictionary = 'return_dictionary' + '_' + file_name + '.npz'
    input_dictionary = np.load(os.path.join(args.directory, signal_extraction_dictionary))

    rms = input_dictionary['rms']
    p2p = input_dictionary['p2p']
    data_centered = input_dictionary['data_centered']
    signal = input_dictionary['signal']
    
    cluster_dictionary = 'return_dict_cluster' + '_' + file_name  + '.npz'
    input_dict_cluster = np.load(os.path.join(args.directory, cluster_dictionary))
    seed =  input_dict_cluster['seed']
    
    n_events = data_centered.shape[0]
    n_frame = data_centered.shape[3]
    
    framex = np.arange(0, n_frame)

    seed_label = 'mV'
    if args.no_calib:
        seed_label = 'ADC'
        
    if args.threshold_kind == 'mv':
        threshold = args.threshold_value
    else:
        with open(os.path.join(args.directory,'Analysis/results_'+ file_name +'.json'), 'r') as file_json:
            data_json = json.load(file_json)
        seed_fit = data_json['seed_1640']
        threshold = args.threshold_value*seed_fit/constants.EL_5_9_KEV
        
    if args.ext_trg_signals is True :
        i = 0
        while seed[i] < threshold or np.isnan(seed[i]):
            i += 1
        args.ev_sel = args.events_min = i
        args.events_max = i+10
        
    fig_sign , ax_sign = plt.subplots(1,2,num='Event plot',figsize=(15,5))
    mat = ax_sign[0].matshow(signal[args.ev_sel,:,:].reshape(4,4),cmap = matplotlib.cm.Blues_r)
    fig_sign.colorbar(mat,ax = ax_sign[0])
    ax_sign[0].set(xlabel='Column',
                  ylabel='Row',
                  title = f'Pixels map: signal number {args.ev_sel}')

    np.gradient(signal)
    c = iter(matplotlib.cm.rainbow(np.linspace(0,1,16)))
    for row in range(4):
        for column in range(4):
            color = next(c)
            ax_sign[1].plot(framex, data_centered[args.ev_sel,row,column,:],".:", color = color, label = f"[{row}][{column}]")

    ax_sign[1].legend(bbox_to_anchor=(1.05, 0.95))
    ax_sign[1].set(xlabel='Frame number',
           ylabel=f'Amplitude ({seed_label})',
           title = f'Pixel signals: signal number {args.ev_sel}',
           xlim=([0, n_frame]))
    fig_sign.savefig(os.path.join(dq_path,'Signal_'+str(args.ev_sel)+ '_' + file_name + '.pdf'))

  
    fig_signals , ax_signals = plt.subplots(1,figsize=(12,6))
    cs = iter(matplotlib.cm.rainbow(np.linspace(0,1,args.events_max - args.events_min)))
    for ev in range(args.events_min,args.events_max):
        color = next(cs)
        for row in range(4):
            for column in range(4):
                if row ==0 and column ==0: ax_signals.plot(framex, data_centered[ev,row,column,:],".:", color = color, label = f"event = {ev}")
                else: ax_signals.plot(framex, data_centered[ev,row,column,:],".:", color = color)
    ax_signals.legend(loc='upper right')
    ax_signals.set(xlabel='Frame number',
           ylabel=f'Amplitude ({seed_label})',
           title = f'Pixel signals, all pixels from event {args.events_min} to {args.events_max-1}',
           xlim=([0, n_frame]))
    fig_signals.savefig(os.path.join(dq_path,'ev_'+str(args.events_min)+'_'+str(args.events_max)+'_signals_' + file_name + '.pdf'))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APTS data quality")
    parser.add_argument('file_in',metavar="file_in", help='Directory and file name with extension for the input file (e.g. apts_20220422_102553.npy) ')
    parser.add_argument('--no_calib','-noc',action = 'store_true',help='Select if you want to disable gain calibration (and take as input data NOT calibrated)')
    parser.add_argument('--directory','-d',default = '.',help='Directory for input files from output of signal_extraction.py')
    parser.add_argument('--cmin',default = 1, type=float, help='For the 2d hist of neighbour - seed: all bins that has count less than cmin will not be displayed (Default: cmin = 1).')
    parser.add_argument('--cmax',default = 800, type=float, help='For the 2d hist of neighbour - seed: all bins that has count more than cmax will not be displayed (Default: cmax = 800).')
    parser.add_argument('--frame_range_min','-frm', default = None, type=int, help='Select the minimum frame for the Frames_apts...pdf plot, from 0 to number of frames. (default n_frames_before - 10)')
    parser.add_argument('--frame_range_max','-frM', default = None, type=int, help='Select the maximum frame for the Frames_apts...pdf plot, from 0 to number of frames. (default n_frames_before + 10)')
    parser.add_argument('--ev_sel', '-evs',default = 5, type = int, help='Select a single event and pixel map you want to see (for plot Signal_xx_apts_yy.pdf), from 0 to the total number of entries (default = 5)')
    parser.add_argument('--events_min', '-evm',default = 0, type=int, help='Select the first event to plot (default = 0) (for plot ev_xx_signals_yy.pdf).')
    parser.add_argument('--events_max', '-evM',default = 10, type=int, help='Select the last event to plot (default = 10) (for plot ev_xx_signals_yy.pdf).')
    parser.add_argument('--ext_trg_signals', '-extrg', action = 'store_true',help='Select if you want to see some signals which is not noise. If true, it will ignore the events selections (ev_sel, events_min, events_max).')
    parser.add_argument('--threshold_kind','-thrk',default='mv',type=str.lower, help='Threshold: mv, el. Kind of threshold to apply (in mV or electrons). Default %(default)s. CAVEAT: electron threshold can be used only if already run the analysis once.',choices=['mv','el'])
    parser.add_argument('--threshold_value','-thrv', type=float,help='Choose the threshold to discharge the noise. Default =  %(default)s.',default = 10)
    parser.add_argument('--rms_p2p', action = 'store_true', help='Select if you want to plot rms and p2p distributions')
    parser.add_argument('--pulse', '-pulse', action = 'store_true',help='Select if you do not want to analyse pulsing data')

    args = parser.parse_args()
        
    data_quality_noise(args)
    if not args.pulse:
        data_quality_frames_hits(args)
    data_quality_signals(args)
