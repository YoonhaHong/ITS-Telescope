#!/usr/bin/env python3

import argparse, json
import glob
import numpy as np
from matplotlib import pyplot as plt
from scipy.optimize import curve_fit
from tqdm import tqdm
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mlr1daqboard import dpts_decoder as decoder
from plotting_utils import plot_parameters
import math
import matplotlib.patches as mpatches

def gaus(x,a,x0,sigma):
    return a*np.exp(-(x-x0)**2/(2*sigma**2))

def lin(x,m,q):
    return m*x+q

def analyse_tot_calibration(npyfile,jsonfile,save_calibration,outdir,vh_cut,calibration,verbose=True):
    if not os.path.exists(outdir): os.makedirs(outdir)
    fname = outdir+'/'+npyfile[npyfile.rfind('/')+1:].replace('.npy','')

    with open(jsonfile) as jf:
        pars = json.load(jf)
    if type(calibration)==str:
        calibration=np.load(calibration)

    # Read data
    data_zs = np.load(npyfile)
    data = np.zeros((32,32,len(pars["vsteps"])), dtype=int)
    n_bad_trains = 0
    n_trains = 0
    n_wf = 0
    n_neigh = 0
    tot_vs_vh_map = [[[] for i in range(32)] for i in range(32)]
    for iv,vh in enumerate(tqdm(pars["vsteps"], desc="Converting data",leave=verbose)):
        for ir,r in enumerate(pars["rows"]):
            for ic,c in enumerate(pars["cols"]):
                data[c,r,iv] = 0
                for inj in range(pars["ninj"]):
                    trains,bad_trains= decoder.zs_to_trains(data_zs[ic,ir,iv,inj])
                    if len(trains)>=2:
                        if calibration is not None:
                            pixels = decoder.trains_to_pix(calibration,trains,bad_trains)
                            if (c,r) in pixels:
                                data[c,r,iv] += 1
                            else:
                                for p in [(c+1,r),(c-1,r),(c,r+1,c,r-1)]:
                                    if p in pixels:
                                        n_neigh += 1
                        else:
                            data[c,r,iv] += 1
                    if (len(trains)==2):
                        tot_vs_vh_map[r][c].append([vh, (trains[1][0]-trains[0][0])*1e9])
                    n_bad_trains += len(bad_trains)
                    n_trains += len(trains)
                    n_wf += 1
    if verbose: 
        print(f"Processed {n_wf} waveforms, found {n_bad_trains} bad edge trains.")
        print(f"Average number of trains per waveform: {n_trains/n_wf}")
        if n_neigh: print(f"In {n_neigh} cases pixel not found in waveform but it neighbour was (possible decoding errors).")

    # Compute ToT mean and std for each pixel, for each value of VH
    tot_vs_vh_mean = [[([],[],[]) for i in range(32)] for i in range(32)]
    mean_tot = []
    for r in pars["rows"]:
        for c in pars["cols"]:
            for vh in pars["vsteps"]:
                for k in range(len(tot_vs_vh_map[r][c])):
                    if (tot_vs_vh_map[r][c][k][0]==vh and vh>vh_cut):
                        mean_tot.append(tot_vs_vh_map[r][c][k][1])
                if (len(mean_tot)>=10):
                    tot_vs_vh_mean[r][c][0].append(vh)
                    tot_vs_vh_mean[r][c][1].append(np.mean(mean_tot))
                    # using the standard deviation of the mean, NOT of the sample:
                    tot_vs_vh_mean[r][c][2].append(np.std(mean_tot,ddof=1)/math.sqrt(len(mean_tot)))
                mean_tot = []

    linear_fit_map = np.zeros((32,32,2))

    # Linear fit of ToT vs VH for each pixel
    # Create m (slope) and q (intercept) map for the calibration
    npt = 0
    xmax = pars["vmax"]
    plt.figure("Fit ToT vs VH")
    plt.title(f"ToT vs VH")
    plt.subplots_adjust(left=0.13, right=0.8)
    for r in pars["rows"]:
        for c in pars["cols"]:
            if(len(tot_vs_vh_mean[r][c][0][:])>0):
                m,q = np.polyfit(tot_vs_vh_mean[r][c][0][:],tot_vs_vh_mean[r][c][1][:],1)
                x = np.linspace(vh_cut,int(pars["vmax"]),200)
                plt.plot(x, lin(x,m,q), color='tab:red',alpha=0.1, linewidth=1)
                linear_fit_map[r,c,0]=m
                linear_fit_map[r,c,1]=q
                npt+=1
            else:
                linear_fit_map[r,c,0]=np.nan
                linear_fit_map[r,c,1]=np.nan
    red_patch = mpatches.Patch(color='tab:red', label='All pixels')
    plt.legend(loc="upper left", handles=[red_patch])
    plt.xlabel("VH (mV)")
    plt.ylabel("ToT (ns)")
    plt.ylim(0,1.4*np.max(tot_vs_vh_mean[15][15][1]))
    plt.xlim(0,xmax)
    plt.grid(axis='both')
    plot_parameters(pars, x=1.01, y=0.7)
    plt.savefig(fname+"_tot_linear_fit.png")

    if verbose:
        print("Linear fit range for ToT vs VH: [",vh_cut,",",pars["vmax"],"] mV")
        print("Number of analyzed pixels: ",npt)

    # If specified, save the calibration maps
    if save_calibration:
        np.save(save_calibration,linear_fit_map)
        print("ToT calibration file saved to:", save_calibration)

    # Some additional plot to visualize the distribution of the parameters
    nbins = 50
    linear_fit_m = np.ravel(linear_fit_map[:,:,0])
    linear_fit_m = linear_fit_m[np.isfinite(linear_fit_m)]
    linear_fit_q = np.ravel(linear_fit_map[:,:,1])
    linear_fit_q = linear_fit_q[np.isfinite(linear_fit_q)]
    
    # 1D distribution m (slope)
    xmin = np.mean(linear_fit_m)-6*np.std(linear_fit_m)
    xmax = np.mean(linear_fit_m)+6*np.std(linear_fit_m)
    plt.figure("single pixel m")
    plt.xlabel('m (ns/mV)')
    plt.title(f'm from linear fit distribution')
    hist,bin_edges,_ = plt.hist(linear_fit_m, range=(xmin,xmax), bins=nbins, \
        label="All pixels: "+str(len(linear_fit_m))+ f"\nMean: {np.mean(linear_fit_m):5.1f} ns\nRMS:  {np.std(linear_fit_m):5.1f} ns")
    bin_mid = (bin_edges[:-1] + bin_edges[1:])/2
    try:
        popt,pcov = curve_fit(gaus, bin_mid, hist, [10,np.mean(linear_fit_m),np.std(linear_fit_m)])
        plt.plot(np.arange(xmin,xmax,xmax/nbins/10),gaus(np.arange(xmin,xmax,xmax/nbins/10),*popt), \
            label=f'$\mu$:    {popt[1]:5.1f} (ns/mV)\n$\sigma$:    {popt[2]:5.1f} (ns/mV)')
    except Exception as e:
        if verbose: print("Fitting error", e)
    plt.legend(loc="upper left", prop={"family":"monospace"})
    plt.xlim(xmin,xmax)
    plot_parameters(pars)
    plt.savefig(fname+"_m_linear_fit.png")

    # 1D distribution q (intercept)
    xmin = np.mean(linear_fit_q)-6*np.std(linear_fit_q)
    xmax = np.mean(linear_fit_q)+6*np.std(linear_fit_q)
    plt.figure("single pixel q")
    plt.xlabel('q (ns)')
    plt.title(f'q from linear fit distribution')
    hist,bin_edges,_ = plt.hist(linear_fit_q, range=(xmin,xmax), bins=nbins, \
        label="All pixels: "+str(len(linear_fit_q))+ f"\nMean: {np.mean(linear_fit_q):5.1f} ns\nRMS:  {np.std(linear_fit_q):5.1f} ns")
    bin_mid = (bin_edges[:-1] + bin_edges[1:])/2
    try:
        popt,pcov = curve_fit(gaus, bin_mid, hist, [10,np.mean(linear_fit_q),np.std(linear_fit_q)])
        plt.plot(np.arange(xmin,xmax,xmax/nbins/10),gaus(np.arange(xmin,xmax,xmax/nbins/10),*popt), \
            label=f'$\mu$:    {popt[1]:5.1f} ns\n$\sigma$:    {popt[2]:5.1f} ns')
    except Exception as e:
        if verbose: print("Fitting error", e)
    plt.legend(loc="upper left", prop={"family":"monospace"})
    plt.xlim(xmin,xmax)
    plot_parameters(pars)
    plt.savefig(fname+"_q_linear_fit.png")

    # m (slope) map
    plt.figure("parameter m map")
    plt.subplots_adjust(left=0.01, right=0.80)
    plt.imshow(linear_fit_map[:,:,0])
    plt.colorbar(pad=0.015).set_label('m (ns/mV)')
    plt.xlabel('Column')
    plt.ylabel('Row')
    plt.title(f'parameter m map')
    plt.text(40, 5, "# pixels: "+str(len(linear_fit_m)))
    plot_parameters(pars, x=1.27, y=0.7)
    plt.savefig(fname+"_mMap.png")

    # q (intercept) map
    plt.figure("parameter q map")
    plt.subplots_adjust(left=0.01, right=0.80)
    plt.imshow(linear_fit_map[:,:,1])
    plt.colorbar(pad=0.015).set_label('q (ns)')
    plt.xlabel('Column')
    plt.ylabel('Row')
    plt.title(f'parameter q map')
    plt.text(40, 5, "# pixels: "+str(len(linear_fit_q)))
    plot_parameters(pars, x=1.27, y=0.7)
    plt.savefig(fname+"_qMap.png")

if __name__=="__main__":
    parser = argparse.ArgumentParser("ToT calibration analysis.",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("file", help="npy or json file created by dpts_threshold.py or directory containing such files.")
    parser.add_argument('--save-calibration', default=None, help="File name of output tot calibration file.")
    parser.add_argument('--outdir' , default="./plots", help="Directory for output plots")
    parser.add_argument('--vh-cut', default=225, type=float, help="Minimum VH of the linear fit range")
    parser.add_argument('-q', '--quiet', action='store_true', help="Do not display plots.")
    parser.add_argument('--decoding-calib', '--calibration', default=None, help="Path to decoding calibration file.")
    args = parser.parse_args()

    if '.npy' in args.file:
        analyse_tot_calibration(args.file,args.file.replace('.npy','.json'),args.save_calibration,args.outdir,args.vh_cut,args.decoding_calib)
    elif '.json' in args.file:
        analyse_tot_calibration(args.file.replace('.json','.npy'),args.file,args.save_calibration,args.outdir,args.vh_cut,args.decoding_calib)
    else:
        if '*' not in args.file: args.file+='*.npy'
        print("Processing all file matching pattern ", args.file)
        for f in tqdm(glob.glob(args.file),desc="Processing file"):
            if '.npy' in f:
                analyse_tot_calibration(f, f.replace('.npy','.json'),args.save_calibration,args.outdir,args.vh_cut,args.decoding_calib,verbose=False)
                plt.close('all')

    if not args.quiet:
        plt.show()
