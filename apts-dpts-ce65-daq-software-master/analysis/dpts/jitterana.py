#!/usr/bin/env python3

import argparse, json
import numpy as np
from matplotlib import pyplot as plt
from tqdm import tqdm
import os
from mlr1daqboard import dpts_decoder as decoder
from plotting_utils import plot_parameters

def timewalkCorrection(tot,a,b,c):
    return a+(b/(tot-c))

def analyse_jitter(npyfile,outdir,timewalk_params):

    if not os.path.exists(outdir): os.makedirs(outdir)
    fname = outdir+'/'+npyfile[npyfile.rfind('/')+1:].replace('.npy','')

    with open(npyfile.replace('.npy','.json')) as jf:
        pars = json.load(jf)

    if type(timewalk_params)==str:
        timewalk_params=np.load(timewalk_params)

    data_zs = np.load(npyfile)
    delta_t = [[] for _ in range(len(pars["vsteps"]))]
    delta_t_corr = [[] for _ in range(len(pars["vsteps"]))]
    VH_values = []
    bad_t0s = []
    n_bad_trains = 0
    n_trains = 0
    n_wf = 0

    for iv in tqdm(range(len(pars["vsteps"])), desc="Converting data"):
        VH_values.append(pars["vsteps"][iv])
        for ir,r in enumerate(pars["rows"]):
            for ic,c in enumerate(pars["cols"]):
                for inj in range(pars["ninj"]):
                    trains,bad_trains = decoder.zs_to_trains(data_zs[ic,ir,iv,inj])
                    delta_t[iv].append(trains[0][0]*1e9)
                    if timewalk_params is not None:
                        delta_t_corr[iv].append(trains[0][0]*1e9 - timewalkCorrection((trains[1][0]-trains[0][0])*1e9,timewalk_params[c][r][0],timewalk_params[c][r][1],timewalk_params[c][r][2]))
                    for edges in bad_trains:
                        bad_t0s.append(edges[0]*1e9)
                    n_bad_trains += len(bad_trains)
                    n_trains += len(trains)
                    n_wf += 1
    print(f"Processed {n_wf} waveforms, found {n_bad_trains} bad edge trains.")
    print(f"Average number of trains per waveform: {n_trains/n_wf}")

    mean_delta_t = []
    mean_delta_t_corr = []
    jitter = []
    jitter_corr = []
    for i in range(len(pars["vsteps"])):
        plt.figure(f"delta_t VH = {VH_values[i]} mV")
        plt.subplots_adjust(left=0.09, right=0.8)
        hist,bin_edges = np.histogram(delta_t[i],'auto')
        plt.hist(delta_t[i],bin_edges,color="red")
        mean_delta_t.append(np.mean(delta_t[i]))
        jitter.append(np.std(delta_t[i]))
        plt.xlabel(r"$\Delta$t (ns)")
        plt.ylabel("entries")
        plt.title(fr'$\Delta$t, VH = {VH_values[i]} mV')
        plt.ylim(0,300)
        plt.xlim(-100,300)
        ax = plt.gca()
        plt.text(0.8, 0.9, f"Mean: {np.mean(delta_t[i]):.2f} ns\nStd dev: {np.std(delta_t[i]):.2f} ns", fontsize = 10,horizontalalignment='center',verticalalignment='center',transform=ax.transAxes,c="red")
        if timewalk_params is not None:
            hist_corr,bin_edges_corr = np.histogram(delta_t_corr[i],'auto')
            plt.hist(delta_t_corr[i],bin_edges_corr,color="blue")
            mean_delta_t_corr.append(np.mean(delta_t_corr[i]))
            jitter_corr.append(np.std(delta_t_corr[i]))
            plt.text(0.78, 0.8, f"Corrected mean: {np.mean(delta_t_corr[i]):.2f} ns\nCorrected std dev: {np.std(delta_t_corr[i]):.2f} ns", fontsize = 10,horizontalalignment='center',verticalalignment='center',transform=ax.transAxes,c="blue")
        plot_parameters(pars,x=1.01,y=0.7)
        plt.savefig(fname+"_delta_t_VH"+str(VH_values[i])+"mV.png")

    plt.figure("Mean delta t")
    plt.subplots_adjust(left=0.1, right=0.8)
    plt.plot(VH_values,mean_delta_t,"ro",label="uncorrected")
    if timewalk_params is not None: plt.plot(VH_values,mean_delta_t_corr,"bo",label="corrected")
    plt.xlabel("VH (mV)")
    plt.ylabel(r"Mean $\Delta$t (ns)")
    plt.title(fr'Mean $\Delta$t')
    plt.legend(loc="upper right", prop={"family":"monospace"})
    plot_parameters(pars,x=1.01,y=0.7)
    plt.savefig(fname+"_mean_delta_t.png")

    plt.figure("Jitter")
    plt.subplots_adjust(left=0.1, right=0.8)
    plt.plot(VH_values,jitter,"ro",label="uncorrected")
    if timewalk_params is not None: plt.plot(VH_values,jitter_corr,"bo",label="corrected")
    plt.xlabel("VH (mV)")
    plt.ylabel(r"Jitter (ns)")
    plt.title(fr'Jitter')
    plt.legend(loc="upper right", prop={"family":"monospace"})
    plot_parameters(pars,x=1.01,y=0.7)
    plt.savefig(fname+"_jitter.png")

if __name__=="__main__":
    parser = argparse.ArgumentParser("Analysis of the jitter on the ToA.",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("npy", help=".npy file created by threshold.py")
    parser.add_argument('--outdir' , default="./plots", help="Directory with output files")
    parser.add_argument('--xlim', default=0, type=int, help="X axis limit")
    parser.add_argument('-q', '--quiet', action='store_true', help="Do not display plots.")
    parser.add_argument('--timewalk-params', default=None, help="Path to timewalk parameters file.")
    args = parser.parse_args()
  
    analyse_jitter(args.npy, args.outdir, args.timewalk_params)

    if not args.quiet: plt.show()
