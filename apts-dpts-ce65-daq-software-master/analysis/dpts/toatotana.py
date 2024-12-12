#!/usr/bin/env python3

import argparse, json
import glob, csv
import numpy as np
from matplotlib import pyplot as plt
from tqdm import tqdm
import os
from mlr1daqboard import dpts_decoder as decoder
from plotting_utils import plot_parameters
from plotting_utils import compute_profile
from collections.abc import Iterable
from lmfit import Model, Parameters

# flattens n dimensional list to 1D
def flatten(l):
    for el in l:
        if isinstance(el, Iterable) and not isinstance(el, (str, bytes)):
            yield from flatten(el)
        else:
            yield el

# fills the two tpyes of ToA depending on the chip version: O, X or S
def fill_toa(pulse_height_type1, pulse_height_type2, toa_type1, toa_type2, vh, toa, r, c, version):
    if version=="X" or version=="S":
        if (c%2==0 and r%2==0) or (c%2!=0 and r%2!=0):
            pulse_height_type1[r][c].append(vh)
            toa_type1[r][c].append(toa)
        if (c%2==0 and r%2!=0) or (c%2!=0 and r%2==0): 
            pulse_height_type2[r][c].append(vh)
            toa_type2[r][c].append(toa)
    elif version=="O":
        if c%2==0:
            pulse_height_type1[r][c].append(vh)
            toa_type1[r][c].append(toa)
        else: 
            pulse_height_type2[r][c].append(vh)
            toa_type2[r][c].append(toa)
    else:
        raise ValueError(f"{version} is an incorrect chip version. Please choose from 'O', 'X' or 'S'.")

# function for ToT vs Vh fit
def totvhFit(x,a,b,c,d):
    return a*x+b-(c/(x-d))

# function for ToA vs Vh fit
def toavhFit(x,a,b,c):
    return a+(b/(x-c))

def analyse_toatot_scan(npyfile,jsonfile,outdir,timewalk_params,thrmapFile,version,pixel=[-1,-1],plot_all=False,verbose=True):
    if not os.path.exists(outdir): os.makedirs(outdir)
    outdir_pix = outdir+'/pixel_plots'
    if not os.path.exists(outdir_pix): os.makedirs(outdir_pix)
    fname = outdir+'/'+npyfile[npyfile.rfind('/')+1:].replace('.npy','')
    fname_pix = outdir_pix+'/'+npyfile[npyfile.rfind('/')+1:].replace('.npy','')

    if thrmapFile is None:
        thrmap = np.full((32,32),100)
        globalThr = 100
    else:
        thr_noise_data = np.load(thrmapFile)
        thrmap = thr_noise_data['thresholds']
        thrmap = thrmap.astype(int)
        # handle bad pixels
        thrmap[thrmap<30] = 0
        thrmap[thrmap>1000] = 0
        globalThr = int(thrmap[thrmap!=0].mean())
        if verbose:
            print(f"Thr max = {np.amax(thrmap[thrmap!=0])}, thr min = {np.amin(thrmap[thrmap!=0])}, thr mean = {thrmap[thrmap!=0].mean()}") 
            print(f"Pixel with max {np.unravel_index(thrmap[thrmap!=0].argmax(), thrmap.shape)}, pixel with min {np.unravel_index(thrmap[thrmap!=0].argmin(), thrmap.shape)}")

    with open(jsonfile) as jf:
        pars = json.load(jf)
    
    if version is None:
        version = pars['version']

    if type(timewalk_params)==str:
        timewalk_params=np.load(timewalk_params)['timewalk_params']
    
    cmap = plt.cm.viridis.copy()
    cmap.set_under(color='white')

    # different vsteps shape if using scripts/dpts/toa_tot_parameter_scan.py
    if isinstance(pars['vsteps'][0], (list,tuple)):
        vsteps_len = len(pars['vsteps'][0][0])
    else:
        vsteps_len = len(pars['vsteps'])

    data_zs = np.load(npyfile)
    n_bad_trains = 0
    n_trains = 0
    n_wf = 0
    pulse_height = [[[] for i in range(32)] for i in range(32)]
    pulse_height_type1 = [[[] for i in range(32)] for i in range(32)]
    pulse_height_type2 = [[[] for i in range(32)] for i in range(32)]
    tot = [[[] for i in range(32)] for i in range(32)]
    toa = [[[] for i in range(32)] for i in range(32)]
    toa_type1 = [[[] for i in range(32)] for i in range(32)]
    toa_type2 = [[[] for i in range(32)] for i in range(32)]
    toa_corr = [[[] for i in range(32)] for i in range(32)]
    for iv in tqdm(range(vsteps_len), desc="Converting data",leave=verbose):
        for ir,r in enumerate(pars["rows"]):
            for ic,c in enumerate(pars["cols"]):
                if pixel[0]!=-1:
                    if (not(r==pixel[0] and c==pixel[1])): continue
                if isinstance(pars['vsteps'][0], (list,tuple)):
                    vh = pars["vsteps"][r][c][iv]
                else:
                    vh = pars["vsteps"][iv]

                for inj in range(pars["ninj"]):
                    trains,bad_trains= decoder.zs_to_trains(data_zs[ic,ir,iv,inj])
                    if len(trains)==0:
                        pulse_height[r][c].append(vh)
                        tot[r][c].append(0)
                        toa[r][c].append(0)
                        fill_toa(pulse_height_type1,pulse_height_type2,toa_type1,toa_type2,vh,0,r,c,version)
                    elif len(trains)==2:
                        pulse_height[r][c].append(vh)
                        tot[r][c].append((trains[1][0]-trains[0][0])*1e6)
                        toa[r][c].append(trains[0][0]*1e9)
                        fill_toa(pulse_height_type1,pulse_height_type2,toa_type1,toa_type2,vh,trains[0][0]*1e9,r,c,version)
                        if timewalk_params is not None:
                          toa_corr[r][c].append(trains[0][0]*1e9 - toavhFit(vh,timewalk_params[r][c][0],timewalk_params[r][c][1],timewalk_params[r][c][2]))
                    n_bad_trains += len(bad_trains)
                    n_trains += len(trains)
                    n_wf += 1

    if verbose: 
        print(f"Processed {n_wf} waveforms, found {n_bad_trains} bad edge trains.")
        print(f"Average number of trains per waveform: {n_trains/n_wf}")
        print("Fitting the ToT and ToA curves for each pixel.")
    
    if plot_all==True: print("Plotting all pixels, this will take a while...")

    # for correted y axis lims
    toa_corr_min = -500
    toa_corr_max = 1000

    # fit the tot vs vh and toa vs tot curves for each pixel and save fit parameters
    fitted_tot_vs_vh_params = np.zeros((32,32,4), dtype=float)
    fitted_timewalk_params = np.zeros((32,32,3), dtype=float)
    tot_vs_vh_chi2 = np.zeros((32,32), dtype=float)
    timewalk_chi2 = np.zeros((32,32), dtype=float)
    for ir,r in enumerate(tqdm(pars["rows"], desc="Row", leave=verbose)):
        for ic,c in enumerate(tqdm(pars["cols"], desc="Col", leave=False)):
            if pixel[0]!=-1:
                if (not(r==pixel[0] and c==pixel[1])): continue
            
            bins_tot_vs_vh_pix = (1200-thrmap[r][c],100)
            bins_toa_vs_vh_pix = (1200-thrmap[r][c],1000)
            bins_toa_corr_vs_vh_pix = (pulse_height[r][c],1000)
            
            # fit tot vs vh
            p_tot_pix, p_tot_pix_mean, p_tot_pix_rms = compute_profile(pulse_height[r][c],tot[r][c],bins_tot_vs_vh_pix)
            try:
                # restrict the fit range
                p_tot_pix_mean_range = p_tot_pix_mean[(p_tot_pix>=thrmap[r][c])]
                p_tot_pix_range = p_tot_pix[(p_tot_pix>=thrmap[r][c])]
                # initial parameter guess
                p0 = [50,-1000,15000,thrmap[r][c]-20]
                # parameter limits
                p_limits=[[-1000,-10000,-1000,-100], [1000, 10000, 1e6,thrmap[r][c]+50]]
                gmodel = Model(totvhFit)
                params = Parameters()
                params.add('a', value=p0[0], min=p_limits[0][0], max=p_limits[1][0])
                params.add('b', value=p0[1], min=p_limits[0][1], max=p_limits[1][1])
                params.add('c', value=p0[2], min=p_limits[0][2], max=p_limits[1][2])
                params.add('d', value=p0[3], min=p_limits[0][3], max=p_limits[1][3])
                resultToT = gmodel.fit(p_tot_pix_mean_range, x=p_tot_pix_range, params=params)
                ToTparam_names = gmodel.param_names
                for ip,par in enumerate(ToTparam_names):
                    fitted_tot_vs_vh_params[r][c][ip] = resultToT.params[par].value
                tot_vs_vh_chi2[r][c] = resultToT.redchi
            except Exception as e:
                if verbose: print(f"ToT vs Vh fitting error for pixel {r} {c}: ", e)
            
            # some ToT shapes have a very sharp curve so are best restricted to (threshold - 5 mV)
            if fitted_tot_vs_vh_params[r][c][2] < 100:
                try:
                    # restrict the fit range
                    p_tot_pix_mean_range = p_tot_pix_mean[(p_tot_pix>=thrmap[r][c]-5)]
                    p_tot_pix_range = p_tot_pix[(p_tot_pix>=thrmap[r][c]-5)]
                    # initial parameter guess
                    p0 = [50,-1000,15000,thrmap[r][c]-20]
                    # parameter limits
                    p_limits=[[-1000,-10000,-1000,-100], [1000, 10000, 1e6,thrmap[r][c]+50]]
                    gmodel = Model(totvhFit)
                    params = Parameters()
                    params.add('a', value=p0[0], min=p_limits[0][0], max=p_limits[1][0])
                    params.add('b', value=p0[1], min=p_limits[0][1], max=p_limits[1][1])
                    params.add('c', value=p0[2], min=p_limits[0][2], max=p_limits[1][2])
                    params.add('d', value=p0[3], min=p_limits[0][3], max=p_limits[1][3])
                    resultToT = gmodel.fit(p_tot_pix_mean_range, x=p_tot_pix_range, params=params)
                    ToTparam_names = gmodel.param_names
                    for ip,par in enumerate(ToTparam_names):
                        fitted_tot_vs_vh_params[r][c][ip] = resultToT.params[par].value
                    tot_vs_vh_chi2[r][c] = resultToT.redchi
                except Exception as e:
                    if verbose: print(f"ToT vs Vh fitting error for pixel {r} {c}: ", e)
        
            # fit toa vs vh
            # remove data with ToA = 0
            pulse_height_reduced = np.array(pulse_height[r][c],dtype=float)
            toa[r][c] = np.array(toa[r][c],dtype=float)
            pulse_height_reduced = pulse_height_reduced[toa[r][c]>0]
            toa[r][c] = toa[r][c][toa[r][c]>0]
            p_toa_pix, p_toa_pix_mean, p_toa_pix_rms = compute_profile(pulse_height_reduced,toa[r][c],bins_toa_vs_vh_pix)
            try:
                # restrict the fit range
                p_toa_pix_mean_range = p_toa_pix_mean[(p_toa_pix>=thrmap[r][c]+0)]
                p_toa_pix_range = p_toa_pix[(p_toa_pix>=thrmap[r][c]+0)]
                # initial parameter guess
                p0 = [50,1e4,thrmap[r][c]-10]
                # parameter limits
                p_limits=[[0, 0, 0], [500, 1e6, thrmap[r][c]+50]]
                gmodel = Model(toavhFit)
                params = Parameters()
                params.add('a', value=p0[0], min=p_limits[0][0], max=p_limits[1][0])
                params.add('b', value=p0[1], min=p_limits[0][1], max=p_limits[1][1])
                params.add('c', value=p0[2], min=p_limits[0][2], max=p_limits[1][2])
                ToAparam_names = gmodel.param_names
                resultToA = gmodel.fit(p_toa_pix_mean_range, x=p_toa_pix_range, params=params)
                for ip,par in enumerate(ToAparam_names):
                    fitted_timewalk_params[r][c][ip]=resultToA.params[par].value
                timewalk_chi2[r][c] = resultToA.redchi
            except Exception as e:
                if verbose: print(f"Timewalk fitting error for pixel {r} {c}: ", e)
            
            if plot_all==True:
                pixel[0]=r
                pixel[1]=c

            # plot chosen pixel
            if r==pixel[0] and c==pixel[1]:
                fig_ToT = plt.figure(f"ToT vs Vh pix {r} {c}")
                plt.title(f"Pix {r} {c}")
                plt.subplots_adjust(left=0.13, right=0.8)
                plt.errorbar(p_tot_pix, p_tot_pix_mean, p_tot_pix_rms,fmt='_', ecolor='k', color='k')
                plt.plot(p_tot_pix_range, resultToT.best_fit, 'r-',
                        label=f"a: {fitted_tot_vs_vh_params[r][c][0]:.4f}\nb: {fitted_tot_vs_vh_params[r][c][1]:.2f}\nc: {fitted_tot_vs_vh_params[r][c][2]:.1f}\nd: {fitted_tot_vs_vh_params[r][c][3]:.1f}\nReduced $\chi^{2}$: {tot_vs_vh_chi2[r][c]:.4f}")
                plt.xlabel("Vh (mV)")
                plt.ylabel(r"ToT ($\mu$s)")
                plt.ylim(0,p_tot_pix_mean[-1]+p_tot_pix_rms[-1]+0.5*p_tot_pix_rms[-1])
                plt.xlim(-10,1210)
                plt.axvline(x=thrmap[r][c])
                plt.legend(loc="upper left", prop={"family":"monospace"})
                plot_parameters(pars, x=1.01)
                plt.savefig(f"{fname_pix}_tot_vs_vh_pix_{r}_{c}.png")
                if plot_all==True: plt.close(fig_ToT)

                fig_toa = plt.figure(f"ToA vs vh pix {r} {c}")
                plt.title(f"Pix {r} {c}")
                plt.subplots_adjust(left=0.13, right=0.8)
                plt.errorbar(p_toa_pix, p_toa_pix_mean, p_toa_pix_rms,fmt='_', ecolor='k', color='k')
                plotx = np.arange(thrmap[r][c],1200,2)
                ploty = toavhFit(plotx,resultToA.params['a'].value,resultToA.params['b'].value,resultToA.params['c'].value)
                plt.plot(plotx, ploty, 'r-',
                        label=f"a: {fitted_timewalk_params[r][c][0]:.4f}\nb: {fitted_timewalk_params[r][c][1]:.0f}\nc: {fitted_timewalk_params[r][c][2]:.1f}\nReduced $\chi^{2}$: {timewalk_chi2[r][c]:.0f}")
                plt.xlabel("Vh (mV)")
                plt.ylabel("ToA (ns)")
                if timewalk_params is not None: plt.ylim(toa_corr_min,toa_corr_max)
                plt.xlim(-10,1210)
                plt.axvline(x=thrmap[r][c])
                plt.legend(loc="upper right", prop={"family":"monospace"})
                plot_parameters(pars, x=1.01)
                plt.savefig(f"{fname_pix}_toa_vs_vh_pix_{r}_{c}.png")
                if plot_all==True: plt.close(fig_toa)
                
                if timewalk_params is not None: 
                    pulse_height_reduced[toa_corr==0] = np.nan
                    toa_corr = np.array(toa_corr)
                    toa_corr[toa_corr==0] = np.nan
                    fig_toa_corr = plt.figure(f"ToA vs Vh pix {r} {c} corrected")
                    plt.title(f"Corrected pix {r} {c}")
                    plt.subplots_adjust(left=0.13, right=0.8)
                    plt.hist2d(pulse_height_reduced,toa_corr[r][c],bins=bins_toa_corr_vs_vh_pix,range=[(0, 1200), (toa_corr_min, toa_corr_max)],cmap=cmap,vmin=1e-10)
                    plt.xlabel("Vh (mV)")
                    plt.ylabel("ToA (ns)")
                    plt.ylim(toa_corr_min,toa_corr_max)
                    plt.xlim(-10,1210)
                    plt.colorbar(pad=0.015)
                    plot_parameters(pars, x=1.25, y=0.7)
                    plt.savefig(f"{fname_pix}_toa_vs_vh_pix_{c}_{r}_corrected.png")
                    if plot_all==True: plt.close(fig_toa_corr)

                # reset pixel
                if plot_all==True:
                    pixel[0]=-1
                    pixel[1]=-1
    
    # if looking at a pixel, don't bother plotting the remaining plots
    if pixel[0]!=-1:
        plt.show()
        exit()
    
    bins = 50

    # reject outliers based on chi2
    d = np.abs(tot_vs_vh_chi2 - np.median(tot_vs_vh_chi2))
    mdev = np.median(d[d!=0])
    s = d/mdev if mdev else 0.
    fitted_tot_vs_vh_params[:,:,0][s>5] = 0
    fitted_tot_vs_vh_params[:,:,1][s>5] = 0
    fitted_tot_vs_vh_params[:,:,2][s>5] = 0
    fitted_tot_vs_vh_params[:,:,3][s>5] = 0
    cut_tot_vs_vh_chi2 = tot_vs_vh_chi2[s>5].flatten()
    tot_vs_vh_chi2[s>5] = 0
    
    d = np.abs(timewalk_chi2 - np.median(timewalk_chi2))
    mdev = np.median(d[d!=0])
    s = d/mdev if mdev else 0.
    fitted_timewalk_params[:,:,0][s>5] = 0
    fitted_timewalk_params[:,:,1][s>5] = 0
    fitted_timewalk_params[:,:,2][s>5] = 0
    cut_timewalk_chi2 = timewalk_chi2[s>5].flatten()
    timewalk_chi2[s>5] = 0

    for ip,par in enumerate(ToTparam_names):  
        # 1D histo of parameter
        plt.figure(f"ToT vs Vh fit param {par}")
        plt.title(f"ToT vs Vh fit param {par}")
        plt.subplots_adjust(left=0.13, right=0.8)
        par_1d = list(flatten(fitted_tot_vs_vh_params[:,:,ip]))
        par_1d = np.array(par_1d)
        par_1d = par_1d[par_1d!=0]
        plt.hist(par_1d,bins=bins)
        plt.xlabel(par)
        plt.ylabel("Counts")
        plot_parameters(pars, x=1.01)
        plt.savefig(f"{fname}_totvhFit_param_{par}.png")

        # map of parameter
        fitted_tot_vs_vh_params[fitted_tot_vs_vh_params==0] = np.nan
        plt.figure(f"ToT vs Vh fit param {par} map")
        plt.title(f"ToT vs Vh fit param {par} map")
        plt.subplots_adjust(left=0.008, right=0.78)
        if ip==1: 
            plt.imshow(abs(fitted_tot_vs_vh_params[:,:,ip]),cmap=cmap)
        else: 
            plt.imshow(fitted_tot_vs_vh_params[:,:,ip],cmap=cmap)
        cbar = plt.colorbar(pad=0.007)
        if np.nanmax(fitted_tot_vs_vh_params[:,:,ip])>1000: cbar.formatter.set_powerlimits((0, 0))
        cbar.set_label(f'ToT vs Vh fit param {par}')
        plt.xlabel('Column')
        plt.ylabel('Row')
        plot_parameters(pars, x=1.24, y=0.7)
        plt.savefig(f"{fname}_totvhFit_param_{par}_map.png")
    
    for ip,par in enumerate(ToAparam_names):  
        # 1D histo of parameter
        plt.figure(f"ToA vs Vh fit param {par}")
        plt.title(f"ToA vs Vh fit param {par}")
        plt.subplots_adjust(left=0.13, right=0.8)
        par_1d = list(flatten(fitted_timewalk_params[:,:,ip]))
        par_1d = np.array(par_1d)
        par_1d = par_1d[par_1d!=0]
        plt.hist(par_1d,bins=bins)
        plt.xlabel(par)
        plt.ylabel("Counts")
        plot_parameters(pars, x=1.01)
        plt.savefig(f"{fname}_timewalk_param_{par}.png")
        
        # map of parameter
        fitted_timewalk_params[fitted_timewalk_params==0] = np.nan
        plt.figure(f"ToA vs Vh fit param {par} map")
        plt.title(f"ToA vs Vh fit param {par} map")
        plt.subplots_adjust(left=0.008, right=0.78)
        plt.imshow(fitted_timewalk_params[:,:,ip],cmap=cmap)
        cbar = plt.colorbar(pad=0.007)
        if np.nanmax(fitted_timewalk_params[:,:,ip])>1000: cbar.formatter.set_powerlimits((0, 0))
        cbar.set_label(f'ToA vs Vh fit param {par}')
        plt.xlabel('Column')
        plt.ylabel('Row')
        plot_parameters(pars, x=1.24, y=0.7)
        plt.savefig(f"{fname}_timewalk_param_{par}_map.png")
    
    bins = 100
    tot_vs_vh_chi2_1d = list(flatten(tot_vs_vh_chi2))
    tot_vs_vh_chi2_1d = np.array(tot_vs_vh_chi2_1d)
    tot_vs_vh_chi2_1d = tot_vs_vh_chi2_1d[tot_vs_vh_chi2_1d!=0]

    # 1D histogram of tot vs vh chi2
    plt.figure("ToT vs Vh fit reduced chi sqr")
    plt.title("ToT vs Vh fit reduced $\chi^{2}$")
    plt.subplots_adjust(left=0.13, right=0.8)
    bins_1 = np.histogram(np.hstack((tot_vs_vh_chi2_1d,cut_tot_vs_vh_chi2)), bins=bins)[1]
    plt.hist(tot_vs_vh_chi2_1d,bins=bins_1)
    if np.any(cut_tot_vs_vh_chi2):
        _,bin_edge,_ = plt.hist(cut_tot_vs_vh_chi2,bins=bins_1)
        plt.axvline(x=np.min(cut_tot_vs_vh_chi2) - (bin_edge[1]-bin_edge[0])/2)
    plt.xlabel(r'Reduced $\chi^{2}$')
    plt.ylabel("Counts")
    plot_parameters(pars, x=1.01)
    plt.savefig(f"{fname}_totvhFit_chi2.png")

    # map of tot vs vh chi2
    tot_vs_vh_chi2[tot_vs_vh_chi2==0] = np.nan
    plt.figure("ToT vs Vh fit reduced chi2 sqr map")
    plt.title("ToT vs Vh fit  reduced $\chi^{2}$ map")
    plt.subplots_adjust(left=0.008, right=0.78)
    plt.imshow(tot_vs_vh_chi2,cmap=cmap)
    cbar = plt.colorbar(pad=0.007)
    cbar.formatter.set_powerlimits((0, 0))
    cbar.set_label(r'Reduced $\chi^{2}$')
    plt.xlabel('Column')
    plt.ylabel('Row')
    plot_parameters(pars, x=1.25, y=0.7)
    plt.savefig(f"{fname}_totvhFit_chi2_map.png")
    
    bins = 50
    timewalk_chi2_1d = list(flatten(timewalk_chi2))
    timewalk_chi2_1d = np.array(timewalk_chi2_1d)
    timewalk_chi2_1d = timewalk_chi2_1d[timewalk_chi2_1d!=0]

    # 1D histogram of timewalk chi2
    plt.figure("ToA vs Vh fit reduced chi sqr")
    plt.title(r"ToA vs Vh fit reduced $\chi^{2}$")
    plt.subplots_adjust(left=0.13, right=0.8)
    bins_1 = np.histogram(np.hstack((timewalk_chi2_1d,cut_timewalk_chi2)), bins=bins)[1]
    plt.hist(timewalk_chi2_1d,bins=bins_1)
    if np.any(cut_timewalk_chi2):
        _,bin_edge,_ = plt.hist(cut_timewalk_chi2,bins=bins_1)
        plt.axvline(x=np.min(cut_timewalk_chi2) - (bin_edge[1]-bin_edge[0])/2)
    plt.xlabel(r'Reduced $\chi^{2}$')
    plt.ylabel("Counts")
    plot_parameters(pars, x=1.01)
    plt.savefig(f"{fname}_timewalk_chi2.png")
    
    # map of timewalk chi2
    timewalk_chi2[timewalk_chi2==0] = np.nan
    plt.figure("ToA vs Vh fit chi2 map")
    plt.title("ToA vs Vh fit chi2 map")
    plt.subplots_adjust(left=0.008, right=0.78)
    plt.imshow(timewalk_chi2,cmap=cmap)
    cbar = plt.colorbar(pad=0.007)
    cbar.formatter.set_powerlimits((0, 0))
    cbar.set_label(r'Reduced $\chi^{2}$')
    plt.xlabel('Column')
    plt.ylabel('Row')
    plot_parameters(pars, x=1.24, y=0.7)
    plt.savefig(f"{fname}_timewalk_chi2_map.png")
    
    np.savez(fname+"_analyzed.npz",tot_params=fitted_tot_vs_vh_params,timewalk_params=fitted_timewalk_params)

if __name__=="__main__":
    parser = argparse.ArgumentParser("Time of Arrival (ToA) and Time over Threshold (ToT) analysis",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("file", help="npy or json file created by threshold.py or directory containing such files.")
    parser.add_argument('--outdir' , default="./plots", help="Directory with output files")
    parser.add_argument('--version' , default=None, help="The chip version to account for column cross-connect or not, either O, X or S. Picked up from json by default.")
    parser.add_argument('-q', '--quiet', action='store_true', help="Do not display plots.")
    parser.add_argument('--timewalk-params', default=None, help="Path to the analysed file (.npz) with the timewalk parameters (ToA vs Vh fit parameters).")
    parser.add_argument('--pixel',nargs="*",type=int,default=[-1,-1],help='Pixel (row and col) to select for plotting.')
    parser.add_argument('--plot-all',action='store_true',help='Plot all the pixel plots (slow!).')
    parser.add_argument('--thrmapFile',default=None, help="Location of analysed threshold scan containing the threshold map. The threshold value of the pixel is used in the fitting range of that pixel. If multiple toa files are being analyses, pass the directory that contains all the analysed threshold results and it will pick up the flist.csv file.")
    args = parser.parse_args()

    if '.npy' in args.file:
        analyse_toatot_scan(args.file, args.file.replace('.npy','.json'),args.outdir,args.timewalk_params,args.thrmapFile,args.version,args.pixel,args.plot_all)
    elif '.json' in args.file:
        analyse_toatot_scan(args.file.replace('.json','.npy'),args.file,args.outdir,args.timewalk_params,args.thrmapFile,args.version,args.pixel,args.plot_all)
    else:
        if '*' not in args.file: args.file+='*.npy'
        thrmap_list = []
        with open(args.thrmapFile+"flist.csv") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if '#' in row['vbb']: continue
                fname=row['fname'] if 'fname' in row else row['thr']
                thrmap_list.append(args.thrmapFile+fname+'_analyzed.npz')
        print("Processing all file matching pattern ", args.file)
        args.file = sorted(glob.glob(args.file))
        thrmap_list = sorted(thrmap_list)
        for i,f in enumerate(tqdm(args.file,desc="Processing file")):
            if '.npy' in f:
                args.thrmapFile = thrmap_list[i]
                analyse_toatot_scan(f, f.replace('.npy','.json'),args.outdir,args.timewalk_params,args.thrmapFile,args.version,args.pixel,args.plot_all,verbose=False)
                plt.close('all')

    if not args.quiet:
        plt.show()

