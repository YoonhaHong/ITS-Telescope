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
import clusterization
import json
import pylandau
import matplotlib.ticker as ticker
import constants
import pathlib

def analysis(args):
    """ analysis takes args, a dictionary with baseline, rms, p2p, data_base, signal  and an other dictionary with cluster variables: seed, seed_index, matrix, cluster_size
    and returns analysis plots: seed, matrix, seed 1 cluster and cluster size histograms """
    
    print('Started analysis...')

    AN_path = os.path.join(args.directory, 'Analysis')
    if not os.path.exists(AN_path):
        os.makedirs(AN_path)
    
    file_name = str(pathlib.PurePosixPath(args.file_in).stem)

    #input_dictionary = signal_extraction(args)
    signal_extraction_dictionary = 'return_dictionary' + '_' + file_name + '.npz'
    input_dictionary = np.load(os.path.join(args.directory, signal_extraction_dictionary))

    #input_dict_cluster = clusterization(args)
    cluster_dictionary = 'return_dict_cluster' + '_' + file_name  + '.npz'
    input_dict_cluster = np.load(os.path.join(args.directory, cluster_dictionary))
    
    signal = input_dictionary['signal']
    seed =  input_dict_cluster['seed']
    cluster_size =  input_dict_cluster['cluster_size']
    matrix =  input_dict_cluster['matrix']
    threshold =  input_dict_cluster['threshold']

    n_event = signal.shape[0]

    signal_ev_pixel = np.zeros((n_event,2,2))

    for ev in range(0,n_event):
         for row in range(1,3):
            for column in range(1,3):
                if np.max(signal[ev,:,:]) == np.max(signal[ev,row,column]):
                    if args.beam_test is False:
                        signal_ev_pixel[ev,row-1,column-1] = np.max(signal[ev,row,column])
                    else:
                        if np.max(signal[ev,row,column]) > threshold:
                            signal_ev_pixel[ev,row-1,column-1] = np.max(signal[ev,row,column])
  
    if args.beam_test is False: max_ampl = int(np.max(signal_ev_pixel))
    else: max_ampl = 5*np.mean(signal_ev_pixel[signal_ev_pixel>threshold])
    bin_width_max_amp= max_ampl/args.number_of_bins

    seed_label = 'mV'
    if args.no_calib:
        seed_label = 'ADC'
        
    fig_max_ampl = plt.figure(figsize=(18,10))
    gs = fig_max_ampl.add_gridspec(2,2,hspace = 0.2,wspace = 0.2, left = 0.05, right = 0.48,)
    ax_max_ampl = gs.subplots(sharex = False, sharey = False)
    for row in range(2):
        for column in range(2):
            y_dummy,x_dummy,_ = ax_max_ampl[row,column].hist(signal_ev_pixel[:,row,column], bins = np.arange(0, max_ampl + bin_width_max_amp, bin_width_max_amp),color = 'mediumblue', label = f"Pixel [{row+1}][{column+1}]", histtype = 'step')
            ax_max_ampl[row,column].set(xlabel=f'Seed pixel signal ({seed_label}) ',
                                 ylabel=f'Frequency (per {round(bin_width_max_amp,2)} {seed_label})',
                                 xlim=([0, max_ampl]),
                                 ylim=([1, 1.5*(y_dummy[1:].max())]))
            ax_max_ampl[row,column].legend(loc='upper right')
    if args.linear_scale == 0:
        for ax in fig_max_ampl.get_axes():
            ax.set_yscale("log")
    
    gs1 = fig_max_ampl.add_gridspec(1, left = 0.55, right = 0.98,hspace = 0.05)

    axNew = gs1.subplots(sharex = False, sharey = False)
    y,x,_ = axNew.hist(seed, bins = np.arange(0, max_ampl + bin_width_max_amp, bin_width_max_amp),color = 'mediumblue', label = f"All 4 central pixels", histtype = 'step')
    axNew.set(xlabel=f'Seed pixel signal ({seed_label}) ',
              ylabel=f'Frequency (per {round(bin_width_max_amp,2)} {seed_label})',
              xlim=([0, max_ampl]),
              ylim=([1, 1.5*(y[1:].max())]))
    axNew.legend(loc='upper right')
    axNew.text(0.01, 0.98, f"Seed threshold = {np.round(threshold,2)} {seed_label}", fontsize=7, transform=axNew.transAxes)
    #axNew.set_xticks(range(0, max_ampl,200))
    if args.linear_scale == 0:
        axNew.set_yscale("log")

    #Definition of functions used in the fit
    def gauss(x, mu, sigma, A):
        return A*np.exp(-(x-mu)**2/2/sigma**2)
    if not (args.no_fit or args.pulse):
        if args.beam_test is False:
            #Searching peak at 1600 electrons
            max_for_fit_y = y[int(max_ampl/bin_width_max_amp)-1]
            i = 1
            index_fit_max = int(max_ampl/bin_width_max_amp) - i
            while max_for_fit_y < 10:
                index_fit_max = int(max_ampl/bin_width_max_amp) - i
                max_for_fit_y = y[index_fit_max]
                max_for_fit_x = x[index_fit_max]
                i += 1
            y_1600 = y[int(0.85*index_fit_max):index_fit_max].max()
            x_1600 = int(x[np.where(y == y_1600)][-1])

            #Settings for the fit
            amp1800 = x_1600*constants.EL_6_5_KEV/constants.EL_5_9_KEV
            freq_amp1800 = y[int(amp1800/bin_width_max_amp)]
            sigma_amp1800 = amp1800/70
            amp1600 = x_1600
            sigma_amp1600 = amp1600/30
            min_fit =  amp1600-sigma_amp1600
            bin_min_fit = int(min_fit/bin_width_max_amp)
            max_fit = amp1800+4*sigma_amp1800
            
            #Definition of functions used in the fit
            def bimodal(x, mu1, sigma1, A1, mu2, sigma2, A2):
                return gauss(x,mu1,sigma1,A1)+gauss(x,mu2,sigma2,A2)
           
            #Fit - start
            x=(x[1:]+x[:-1])/2
            x = x[bin_min_fit:]
            y = y[bin_min_fit:]
            try:
                expected = (amp1600, sigma_amp1600, freq_amp1800*10, amp1800, sigma_amp1800, freq_amp1800) #mu1, sigma1, A1, mu2, sigma2, A2
                params, cov = curve_fit(bimodal, x, y, expected, bounds=([min_fit,0,0,amp1600,0,0], np.inf))
                sigma = np.sqrt(np.diag(cov))
                x_fit = np.linspace(min_fit, max_fit, 500)
                #plot combined...
                plt.plot(x_fit, bimodal(x_fit, *params), color = 'mediumblue', lw = 3, label = 'Double Gaussian')
                #individual Gauss curves
                plt.plot(x_fit, gauss(x_fit, *params[:3]), color = 'mediumblue', lw = 1, ls="--", label = 'Gaussian - 1640')
                plt.plot(x_fit, gauss(x_fit, *params[3:]), color = 'mediumblue', lw = 1, ls=":", label = 'Gaussian - 1800')
                plt.legend()
                print('Seed : Fit parameters')
                fit_results_seed = [('Mean1', params[0]),
                                    ('Sigma1', params[1]),
                                    ('A1', params[2]),
                                    ('Mean2', params[3]),
                                    ('Sigma2', params[4]),
                                    ('A2', params[5])]
                for name, value in fit_results_seed:
                    outstr = "{:6s}: {:7.2f}".format(name, value)
                    print(outstr)
            except RuntimeError:
                print("Error - double gaussian fit failed for seed, trying with a single gaussian around the peak at 1600 electrons.")
                expected = (amp1600, sigma_amp1600, freq_amp1800*10) #mu1, sigma1, A1
                params, cov = curve_fit(gauss, x, y, expected, bounds=([0,0,0,amp1600,0,0], np.inf))
                sigma = np.sqrt(np.diag(cov))
                x_fit = np.linspace(min_fit, max_fit, 500)
                plt.plot(x_fit, gauss(x_fit, *params),color = 'mediumblue', lw = 3)
                print('Seed : Fit parameters')
                fit_results_seed = [('Mean', params[0]),
                                      ('Sigma', params[1]),
                                      ('A', params[2])]
                for name, value in fit_results_seed:
                    outstr = "{:6s}: {:7.2f}".format(name, value)
                    print(outstr)
            #Fit - end
            
        #Fit for beam test start
        else:
            bin_min_fit = int(threshold/bin_width_max_amp)
            x=(x[1:]+x[:-1])/2
            x = x[bin_min_fit:]
            y = y[bin_min_fit:]
            freq_amp_max = int(y.max())
            mean_bt = np.mean(seed[seed>threshold])
            sigma_bt =  np.sqrt(mean_bt)
            x_fit = np.linspace(threshold, max_ampl, freq_amp_max)
            expected_langaus = (mean_bt,sigma_bt,sigma_bt, freq_amp_max) #mpv, eta, sigma, A
            params, pcov  = curve_fit(pylandau.langau, x, y, expected_langaus,bounds=([threshold,0.1*sigma_bt,0.1*sigma_bt,0.8*freq_amp_max],[mean_bt,10*sigma_bt,5*sigma_bt,2*freq_amp_max]))
            #expected_landau = (mean_bt, eta, freq_amp_max) #mpv, eta, A
            #coeff, pcov  = curve_fit(pylandau.landau, x, y, expected_landau,bounds=([mean_bt/5,1,10],[5*mean_bt,5*sigma_bt,np.inf] ))
            # Plot
            #plt.errorbar(x, y, np.sqrt(pylandau.langau(x, *coeff)), fmt=".")
            sigma = np.sqrt(np.diag(pcov))
            fit_results_seed = [('MPV', params[0]),
                                ('Eta', params[1]),
                                ('Sigma', params[2]),
                                ('A', params[3])]
            for name, value in fit_results_seed:
                outstr = "{:6s}: {:7.2f}".format(name, value)
                print(outstr)
            plt.plot(x_fit, pylandau.langau(x_fit, *params), "-",color = 'mediumblue', label = f'MPV = {round(params[0],2)} {seed_label}')
            plt.legend()
        #Fit for beam test ends

    fig_max_ampl.savefig(os.path.join(AN_path,'Seed_signals_4_central_pixels' + '_' + file_name + '.pdf'))
  
    fig_ampl_matrix_seed_1 = plt.figure(figsize=(18,10))
    gs1seed = fig_ampl_matrix_seed_1.add_gridspec(2,2,hspace = 0.2,wspace = 0.2, left = 0.05, right = 0.48,)
    ax_ampl_matrix_seed_1 = gs1seed.subplots(sharex = False, sharey = False)
    for row in range(2):
        for column in range(2):
            y_dummy1,x_dummy1,_ = ax_ampl_matrix_seed_1[row,column].hist(signal_ev_pixel[:,row,column][cluster_size == 1], bins = np.arange(0, max_ampl + bin_width_max_amp, bin_width_max_amp),color = 'dodgerblue', label = f"Pixel [{row+1}][{column+1}]", histtype = 'step')
            ax_ampl_matrix_seed_1[row,column].set(xlabel=f'Seed for cluster size = 1 ({seed_label}) ',
                                 ylabel=f'Frequency (per {round(bin_width_max_amp,2)} {seed_label})',
                                 xlim=([0, max_ampl]),
                                 ylim=([1, 1.5*(y_dummy1[1:].max())]))
            ax_ampl_matrix_seed_1[row,column].legend(loc='upper right')
    if args.linear_scale == 0:
        for ax in fig_ampl_matrix_seed_1.get_axes():
            ax.set_yscale("log")
        
    
    gs1seed4 = fig_ampl_matrix_seed_1.add_gridspec(1, left = 0.55, right = 0.98,hspace = 0.05)
    ax_new1seed = gs1seed4.subplots(sharex = False, sharey = False)
    yM,xM,_ = ax_new1seed.hist(matrix[cluster_size>0],bins = np.arange(0, max_ampl + bin_width_max_amp, bin_width_max_amp), color = 'orangered', label = f"Matrix signal", histtype = 'step', range=[0, max_ampl])
    y1,x1,_ = ax_new1seed.hist(seed[cluster_size == 1], bins = np.arange(0, max_ampl + bin_width_max_amp, bin_width_max_amp),color = 'dodgerblue', label = f"Seed pixel signal for cluster size = 1, 4 central pixels", histtype = 'step', range=[0, max_ampl])
    ax_new1seed.set(xlabel=f'Seed pixel signal for cluster size = 1 ({seed_label}) ',
              ylabel=f'Frequency (per {round(bin_width_max_amp,2)} {seed_label})',
              xlim=([0, max_ampl]),
              ylim=([1, 1.5*(yM[1:].max())]))
    ax_new1seed.legend(loc='upper right')
    ax_new1seed.text(0.01, 0.98, f"Seed threshold = {np.round(threshold,2)} {seed_label}", fontsize=7, transform=ax_new1seed.transAxes)
    #ax_new1seed.set_xticks(range(0, max_ampl))
    if args.linear_scale == 0:
        ax_new1seed.set_yscale("log")
    if not (args.no_fit or args.pulse):
        if args.beam_test is False:
            #Fit - start for matrix
            min_fit_matrix = amp1600-5*sigma_amp1600
            bin_min_fit_matrix = int(min_fit_matrix/bin_width_max_amp)
            max_fit_matrix = amp1600+4*sigma_amp1600
            xM=(xM[1:]+xM[:-1])/2
            xM = xM[bin_min_fit_matrix:]
            yM = yM[bin_min_fit_matrix:]
            expected_matrix = (amp1600, sigma_amp1600, freq_amp1800*10) #mu1, sigma1, A1
            paramsM, covM = curve_fit(gauss, xM, yM, expected_matrix)
            sigmaM = np.sqrt(np.diag(covM))
            x_fitM = np.linspace(min_fit_matrix, max_fit_matrix, 500)
            #Fitting a second time in order to have a centered fit
            expected_matrix = (paramsM[0], paramsM[1], paramsM[2]) #mu1, sigma1, A1
            paramsM, covM = curve_fit(gauss, xM, yM, expected_matrix)
            x_fitM = np.linspace(paramsM[0]-1.5*paramsM[1], paramsM[0]+1.5*paramsM[1], 500)
            plt.plot(x_fitM, gauss(x_fitM, *paramsM),color = 'orangered', lw = 4)
            print('Matrix : Fit parameters')
            fit_results_matrix = [('Mean', paramsM[0]),
                                  ('Sigma', paramsM[1]),
                                  ('A', paramsM[2])]
            for name, value in fit_results_matrix:
                outstr = "{:6s}: {:7.2f}".format(name, value)
                print(outstr)
            #Fit - end for matrix

            #Fit - start for seed 1 cluster
            x1=(x1[1:]+x1[:-1])/2
            x1 = x1[bin_min_fit:]
            y1 = y1[bin_min_fit:]
            try:
                expected = (amp1600, sigma_amp1600, freq_amp1800*10, amp1800, sigma_amp1800, freq_amp1800) #mu1, sigma1, A1, mu2, sigma2, A2
                params1, cov1 = curve_fit(bimodal, x1, y1, expected, bounds=([0,0,0,amp1600,0,0], np.inf))
                sigma1 = np.sqrt(np.diag(cov1))
                x_fit1 = np.linspace(min_fit, max_fit, 500)
                plt.plot(x_fit1, bimodal(x_fit1, *params1),color = 'dodgerblue', lw = 4)
                print('Seed 1 cluster : Fit parameters')
                fit_results_seed1cl = [('Mean1', params1[0]),
                                       ('Sigma1', params1[1]),
                                       ('A1', params1[2]),
                                       ('Mean2', params1[3]),
                                       ('Sigma2', params1[4]),
                                       ('A2', params1[5])]
                for name, value in fit_results_seed1cl:
                    outstr = "{:6s}: {:7.2f}".format(name, value)
                    print(outstr)
            except RuntimeError:
                print("Error - double gaussian fit failed for seed when cluster =1 , trying with a single gaussian around the peak at 1600 electrons.")
                expected = (amp1600, sigma_amp1600, freq_amp1800*10) #mu1, sigma1, A1
                params1, cov1 = curve_fit(gauss, x1, y1, expected, bounds=([0,0,0,amp1600,0,0], np.inf))
                sigma1 = np.sqrt(np.diag(cov1))
                x_fit1 = np.linspace(min_fit, max_fit, 500)
                plt.plot(x_fit1, gauss(x_fit1, *params1),color = 'dodgerblue', lw = 4)
                print('Seed 1 cluster: Fit parameters')
                fit_results_seed1cl = [('Mean', params1[0]),
                                      ('Sigma', params1[1]),
                                      ('A', params1[2])]
                for name, value in fit_results_seed1cl:
                    outstr = "{:6s}: {:7.2f}".format(name, value)
                    print(outstr)
            #Fit - end for seed 1 cluster
    fig_ampl_matrix_seed_1.savefig(os.path.join(AN_path,'Matrix_Seed1Cluster'+ '_' + file_name +'.pdf'))

    fig_seed_matrix , ax_seed_matrix = plt.subplots(1,figsize = (7,6))
    #ax_seed_matrix = fig_seed_matrix.subplots(sharex = False, sharey = False)
    yMs,xMs,_ = ax_seed_matrix.hist(matrix[cluster_size>0],bins = np.arange(0, max_ampl + bin_width_max_amp, bin_width_max_amp), color = 'orangered', label = f"Matrix signal", histtype = 'step')
    ax_seed_matrix.hist(seed[:], bins = np.arange(0, max_ampl + bin_width_max_amp, bin_width_max_amp),color = 'mediumblue', label = f"Seed signal, 4 central pixels ", histtype = 'step')
    ax_seed_matrix.set(xlabel=f'Seed pixel signal ({seed_label}) ',
              ylabel=f'Frequency (per {round(bin_width_max_amp,2)} {seed_label})',
              xlim=([0, max_ampl]),
              ylim=([1, 1.5*(yMs[1:].max())]))
    ax_seed_matrix.legend(loc='upper left')
    ax_seed_matrix.text(0.775, 0.98, f"Seed threshold = {np.round(threshold,2)} {seed_label}", fontsize=7, transform=ax_seed_matrix.transAxes)
    #ax_seed_matrix.set_xticks(range(0, max_ampl))
    if args.linear_scale == 0:
        ax_seed_matrix.set_yscale("log")

    fig_seed_matrix.savefig(os.path.join(AN_path,'Matrix_Seed'+ '_' + file_name +'.pdf'))

    fig_seed_all_clusters , ax_seed_all_clusters = plt.subplots(1,figsize = (7,4))
    #['#00429d', '#416db1', '#629cc4', '#7dccd7', '#96ffea', '#ffbcaf', '#f4777f', '#cf3759', '#93003a']
    colors = ["#00429d","#629cc4","#f4777f","#93003a"]
    lables = ['Cluster size = 1', r'Cluster size $\leq$ 2', r'Cluster size $\leq$ 3', r'Cluster size $\leq$ 4']
    yCa,xCa,_ = ax_seed_all_clusters.hist([seed[cluster_size == 1], seed[cluster_size == 2], seed[cluster_size == 3], seed[cluster_size == 4]], bins = np.arange(0, max_ampl + bin_width_max_amp, bin_width_max_amp),label = lables,color = colors, histtype = 'stepfilled', alpha=1.,stacked=True)
   
    ax_seed_all_clusters.set(xlabel=f'Seed pixel signal ({seed_label}) ',
              ylabel=f'Frequency (per {round(bin_width_max_amp,2)} {seed_label})',
              xlim=([0, max_ampl]),
              ylim=([1, 1.6*(yCa[1:].max())])
              )
    ax_seed_all_clusters.legend(loc='upper left', bbox_to_anchor=(1., 1.))
    ax_seed_all_clusters.text(0.01, 0.97, f"Seed threshold = cluster threshold = {np.round(threshold,2)} {seed_label}", fontsize=7, transform=ax_seed_all_clusters.transAxes)
    #ax_seed_all_clusters.set_xticks(range(0, max_ampl))
    if args.linear_scale == 0:
        ax_seed_all_clusters.set_yscale("log")
    fig_seed_all_clusters.tight_layout()
    fig_seed_all_clusters.savefig(os.path.join(AN_path,'Seed_All_Clusters'+ '_' + file_name +'.pdf'))

    fig_matrix_all_clusters , ax_matrix_all_clusters = plt.subplots(1,figsize = (7,4))
    yCa,xCa,_ = ax_matrix_all_clusters.hist([matrix[cluster_size == 1], matrix[cluster_size == 2], matrix[cluster_size == 3], matrix[cluster_size == 4]], bins = np.arange(0, max_ampl + bin_width_max_amp, bin_width_max_amp),label = lables,color = colors, histtype = 'stepfilled', alpha=1.,stacked=True)
  
    ax_matrix_all_clusters.set(xlabel=f'Matrix signal ({seed_label}) ',
              ylabel=f'Frequency (per {round(bin_width_max_amp,2)} {seed_label})',
              xlim=([0, max_ampl]),
              ylim=([1, 1.6*(yCa[1:].max())])
              )
    ax_matrix_all_clusters.legend(loc='upper left', bbox_to_anchor=(1., 1.))
    ax_matrix_all_clusters.text(0.01, 0.97, f"Cluster threshold = {np.round(threshold,2)} {seed_label}", fontsize=7, transform=ax_matrix_all_clusters.transAxes)
    if args.linear_scale == 0:
        ax_matrix_all_clusters.set_yscale("log")
    fig_matrix_all_clusters.tight_layout()
    fig_matrix_all_clusters.savefig(os.path.join(AN_path,'Matrix_All_Clusters'+ '_' + file_name +'.pdf'))

    max_hist_cluster = 10
    bin_width_cluster = 1
    fig_cluster , ax_cluster = plt.subplots(1,figsize = (7,6))
    #cs = iter(matplotlib.cm.viridis(np.linspace(0,1,args.events)))
    ax_cluster.hist(cluster_size[cluster_size>0],bins = np.arange(0, max_hist_cluster + bin_width_cluster, bin_width_cluster), color = 'mediumblue', label = f"Cluster size for threshold = {np.round(threshold,2)} {seed_label}", histtype = 'step', density = True)
    ax_cluster.set(xlabel = 'Cluster size',
       ylabel = 'Relative frequency',
       title = 'Cluster size',
       xlim = ([1, max_hist_cluster]))
    ax_cluster.legend(loc='upper right')
    #Center label between ticks
    ax_cluster.xaxis.set_major_formatter(ticker.NullFormatter())
    ax_cluster.xaxis.set_minor_locator(ticker.FixedLocator(np.arange(1.5,10.5,1)))
    ax_cluster.xaxis.set_minor_formatter(ticker.FixedFormatter(range(1,11)))
    for tick in ax_cluster.xaxis.get_minor_ticks():
        tick.tick1line.set_markersize(0)
        tick.tick2line.set_markersize(0)
    fig_cluster.savefig(os.path.join(AN_path,'Cluster_Size'+ '_' + file_name +'.pdf'))
    
    #output for results_apts
    with open(str(pathlib.PurePosixPath(args.file_in).with_suffix('.json')), 'r') as file_json:
        data_json = json.load(file_json)
    
    rms = input_dictionary['rms']
    p2p = input_dictionary['p2p']
    noise = input_dictionary['noise']
    mean_cluster_size = np.nanmean(cluster_size[cluster_size>0])
    
    if not (args.no_fit or args.pulse):
        if args.beam_test is False:
            CCE = 100*paramsM[0]/params1[0];
            Capacitance = constants.EL_5_9_KEV*constants.Q_E*pow(10,3)/(params[0]);
            dN = np.sqrt(constants.EL_5_9_KEV*constants.FANO_SIL)*params[0]/constants.EL_5_9_KEV;#uncertainty, given in mV, due to Fano factor=0.116
            
            try:
                seed1800 = params[3]
                seed1cl1800 = params1[3]
            except IndexError:
                print("Error - No value found for peak at 1800 electrons")
                seed1800 = None
                seed1cl1800 = None
            
            results ={
                "seed_1640" : params[0],
                "seed_1640_err" : sigma[0],
                "seed1cl_1640" : params1[0],
                "matrix_1640" : paramsM[0],
                "noise" : np.mean(np.std(noise[:,:,:], axis=0)),
                "RMS" : np.mean(rms[:,:,:]),
                "p2p" : np.mean(p2p[:,:,:]),
                "sgm_seed_1640" : params[1],
                "sgm_seed_err" : sigma[1],
                "sgm_seed1cl_1640" : params1[1],
                "sgm matrix_1640" : paramsM[1],
                "sgm_1cl_DIV_sgm_matr" : params1[1]/paramsM[1],
                "dN" : dN,
                "seed_1800" : seed1800,#ADC
                "seed1cl_1800" : seed1cl1800,
                "CCE" : CCE,#%
                "C" : Capacitance,#fF
                "Mean_cluster_size" : mean_cluster_size,
                "Threshold" : threshold.tolist(),
                "Unit" : seed_label
            }
        else:
            results ={
                "noise" : np.mean(np.std(noise[:,:,:], axis=0)),
                "RMS" : np.mean(rms[:,:,:]),
                "p2p" : np.mean(p2p[:,:,:]),
                "seed_mpv" : params[0],
                "seed_mpv_err" : sigma[0],
                "Mean_cluster_size" : mean_cluster_size,
                "Threshold" : threshold.tolist(),
                "Unit" : seed_label
            }
        
    elif args.pulse:
        with open('library_seed_1640.json', 'r') as file_lib:
            library_seed_1640 = json.load(file_lib)
        chip_ID = data_json['chip_ID']
        vbb = data_json['vbb']
        seed_1640 = [entry for entry in library_seed_1640["library_seed_1640"] if (entry["chip_ID"] == chip_ID and entry["vbb"] == vbb) ]
        seed_1640 = [entry["seed_1640"] for entry in seed_1640]
        try:
            seed_1640 =  float(seed_1640[0])
            C_pulsing = 1.e18*np.nanmean(seed) * constants.EL_5_9_KEV * constants.Q_E/(data_json['vh']*seed_1640*1e-3)
        except IndexError:
            print("Error - No value found in library_seed_1640 for this chip and voltage. Pulsing capacitance set to None.")
            C_pulsing = None
        results ={
            "seed_mean" : np.nanmean(seed),
            "C_pulsing": C_pulsing,
            "noise" : np.mean(np.std(noise[:,:,:], axis=0)),
            "RMS" : np.mean(rms[:,:,:]),
            "p2p" : np.mean(p2p[:,:,:]),
            "Mean_cluster_size" : mean_cluster_size,
            "Threshold" : threshold.tolist(),
            "Unit" : seed_label
        }
    elif args.no_fit and not args.pulse:
        results ={
            "noise" : np.mean(np.std(noise[:,:,:], axis=0)),
            "RMS" : np.mean(rms[:,:,:]),
            "p2p" : np.mean(p2p[:,:,:]),
            "Mean_cluster_size" : mean_cluster_size,
            "Threshold" : threshold.tolist(),
            "Unit" : seed_label
        }
    
    dict_combined = dict(list(data_json.items()) + list(results.items()))
    json_object = json.dumps(dict_combined, indent = 4)
    with open(os.path.join(AN_path,'results_'+ file_name + '.json'), "w") as outfile:
        outfile.write(json_object)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APTS signal extraction")
    parser.add_argument('file_in',metavar="file_in", help='Directory and file name with extension for the input file (e.g. apts_20220422_102553.npy) ')
    parser.add_argument('--no_calib','-noc',action = 'store_true',help='Select if you want to disable gain calibration (and take as input data NOT calibrated)')
    parser.add_argument('--directory','-d',default = '.',help = 'Directory for input files from output of signal_extraction.py and clusterization.py.')
    parser.add_argument('--linear_scale', '-ls', action = 'store_true',help='Select if you want to plot the signal plots with linear scale (Default log scale)')
    parser.add_argument('--number_of_bins','-nob',type = int, default = 200,help='Number of bins for plots of signal distribution. Default 200.')
    parser.add_argument('--beam_test', '-bt', action = 'store_true',help='Select if you want to analyse beam test data')
    parser.add_argument('--no_fit', '-nof', action = 'store_true',help='Select if you do not want to fit the spectra')
    parser.add_argument('--rms_p2p', action = 'store_true', help='Select if you want to plot rms and p2p distributions')
    parser.add_argument('--pulse', '-pulse', action = 'store_true',help='Select if you do not want to analyse pulsing data')

    args = parser.parse_args()
    
    analysis(args)
