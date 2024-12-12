#!/usr/bin/env python3

import argparse, json
import glob
import numpy as np
from matplotlib import pyplot as plt
from tqdm import tqdm
import os
from pathlib import Path
from mlr1daqboard import dpts_decoder as decoder
from plotting_utils import plot_parameters
from matplotlib.colors import LogNorm

def ml_masking(gids,pids,min_hits):
    import hdbscan

    X = np.array(list(zip(gids,pids)))
    
    model = hdbscan.HDBSCAN(min_cluster_size=min_hits,cluster_selection_epsilon=0.01).fit(X)
    labels = model.labels_
    # cut on the probability that a point is part of a cluster
    # removes neighbouring pixels from the cluster without setting epsilon too low
    prob = model.probabilities_
    prob_cut = 0.1
    
    ul = [i for i in set(labels) if i>-1]
    n_masked   = int(len(ul)) if ul else 0
    masked     = X[prob>prob_cut]
    not_masked = X[prob<prob_cut]
    labels     = labels[prob>prob_cut]
    masked_gps = [np.mean(masked[labels==i],axis=0) for i in ul]

    return n_masked,masked,not_masked,masked_gps

def analyse_fhr(npyfile,jsonfile,calibration,outdir,noise_cut,mask,verbose=True):
    if not os.path.exists(outdir): os.makedirs(outdir)
    fname = os.path.join(outdir,Path(npyfile).stem)

    with open(jsonfile) as jf:
        pars = json.load(jf)
        
    if calibration is not None:
        if "_rising.npy" in calibration:
            calibration_fall=calibration.replace("_rising.npy","_falling.npy")
        else:
            calibration_fall=calibration.replace(".npy","_falling.npy")
        calibration=np.load(calibration)
        calibration_fall=np.load(calibration_fall)

    if mask is not None:
        if mask.endswith('.txt'):
            mask = np.loadtxt(mask)
        else:
            mask = np.load(mask)
        if mask.shape==(2,):
            mask = np.array([mask])
        if verbose:
            print("Using a mask:")
            print(mask)

    if "interrupted" in pars:
        print("The scan was interrupted: analysis not supported.", pars['interrupted'])
        return False

    data_zs = np.load(npyfile)
    data_pixels = np.zeros((32,32), dtype=int)
    data_pixels_masked = np.zeros((32,32), dtype=int)
    n_hits = 0
    n_hits_max = 0 # count every train in an event as a hit
    n_hits_min = 0 # only increase the hit count by one for an event with trains 
    n_hits_masked = 0
    n_bad_trains = 0
    n_trains = 0
    n_wf = 0
    n_zero_events  = 0 # number of events with 0 trains
    n_one_events   = 0 # number of events with 1 train
    n_two_events   = 0 # number of events with 2 trains
    n_multi_events = 0 # number of events with >2 trains

    max_trains = 10
    pids = [[] for _ in range(max_trains)]
    gids = [[] for _ in range(max_trains)]
    pids_masked = [[] for _ in range(max_trains)]
    gids_masked = [[] for _ in range(max_trains)]

    # Get all rising edges of hits, assume all rising edges of hits come first
    # used as input to ml masking to mask
    pids_hit = []
    gids_hit = []

    # get gids and pids of train 0 of trains of length 2
    # used as input to ml masking to get totalnoisy
    pids_lentwo = [] 
    gids_lentwo = []

    eventTime = 4.001e-5 # 40.01 us

    # sensitivity limit of the measurement
    senselimit = 1/(pars['ntrg']*eventTime*1024)
    
    for inj in tqdm(range(pars["ntrg"]),desc="Converting data",leave=verbose):
        trains,bad_trains = decoder.zs_to_trains(data_zs[inj])
        trains_masked = trains.copy()
        if len(trains)>0:
            n_hits += int(np.ceil(len(trains)/2))
            n_hits_max += len(trains)
            n_hits_min += 1
            for i,edges in enumerate(trains):
                pids[i].append((edges[2]-edges[0])*1e9)
                gids[i].append((edges[3]-edges[2])*1e9)
                if len(trains)==2 and i==0:
                    pids_lentwo.append((edges[2]-edges[0])*1e9)
                    gids_lentwo.append((edges[3]-edges[2])*1e9)
            
            for j in range(int(len(trains)/2+0.5)):
                pids_hit.append((trains[j][2]-trains[j][0])*1e9)
                gids_hit.append((trains[j][3]-trains[j][2])*1e9)
            if calibration is not None:
                # assume falling rising pairs
                pixels = decoder.trains_to_pix((calibration,calibration_fall),trains,bad_trains,fhr=True)
                trains_len = len(trains)
                pixels_r = pixels[0]
                pixels_f = pixels[1]
                pixels_reorder = []
                pixels_tmp_len = len(pixels_r) + len(pixels_f)
                for i in range(len(pixels_r)):
                    pixels_reorder.append(pixels_r[i])
                    if not pixels_f: continue
                    if pixels_tmp_len%2==1 and i==pixels_tmp_len-np.ceil(pixels_tmp_len/2): continue
                    pixels_reorder.append(pixels_f[i])
                pixels = pixels_reorder
                for i in reversed(range(trains_len)):
                    data_pixels[pixels[i]] += 1
                    if mask is not None:
                        if pixels[i][0] in mask[:,0] and pixels[i][1] in mask[:,1]:
                            trains_masked.pop(i)
                        else:
                            data_pixels_masked[pixels[i]] += 1
                            pids_masked[i].append((trains[i][2]-trains[i][0])*1e9)
                            gids_masked[i].append((trains[i][3]-trains[i][2])*1e9)
                n_hits_masked += int(np.ceil(len(trains_masked)/2))
        else:
            n_zero_events+=1
        
        # handle the not so nice events
        if len(trains)==1:
            n_one_events+=1
        elif len(trains)==2:
            n_two_events+=1
        elif len(trains)>2:
            n_multi_events+=1
        
        # remove bad trains who have a len==2 and whose edges are very close
        for i,edges in reversed(list(enumerate(bad_trains))):
            if len(edges)==2:
                edge_diff = (edges[1]-edges[0])*1e9
                if edge_diff < 0.3:
                    bad_trains.pop(i)
                    continue
        
        n_hits += len(bad_trains)*2
        n_hits_max += len(bad_trains)*2
        n_hits_min += len(bad_trains)*2
        if mask is not None: n_hits_masked += len(bad_trains)*2
        n_bad_trains += len(bad_trains)
        
        n_trains += len(trains)
        n_wf += 1

    max_trains = next((i for i in range(max_trains) if len(pids[i])==0),5)

    noiseocc = n_hits/(1024*eventTime*n_wf)
    noiseocc_max = n_hits_max/(1024*eventTime*n_wf)
    noiseocc_min = n_hits_min/(1024*eventTime*n_wf)
    if noiseocc==0: noiseocc = senselimit
    if noiseocc_max==0: noiseocc_max = senselimit
    if noiseocc_min==0: noiseocc_min = senselimit
    
    # calculate statistical error and fractional statistical error
    stat_err = np.sqrt(n_hits)/(1024*eventTime*n_wf)
    stat_err_frac = stat_err/noiseocc
    # calculate the systematic error and fractional systematic error
    sys_err = [noiseocc - noiseocc_min, noiseocc_max - noiseocc]
    sys_err_frac = [sys_err[0]/noiseocc, sys_err[1]/noiseocc]
    # calculate total error, add the fractional sys and fractional stat error in quadrature
    noiseocc_err_frac = [np.sqrt(stat_err_frac**2 + sys_err_frac[0]**2), np.sqrt(stat_err_frac**2 + sys_err_frac[1]**2)]
    noiseocc_err = [noiseocc*noiseocc_err_frac[0], noiseocc*noiseocc_err_frac[1]]
    
    totalnoisy = 0
    noiseocc_masked = noiseocc
    noiseocc_masked_err = [0, 0]

    if calibration is not None:
        totalnoisy = np.count_nonzero(data_pixels[data_pixels>=10])
        
        noiseocc_masked = (n_hits_masked)/(1024*eventTime*n_wf)
        if noiseocc_masked==0: noiseocc_masked = senselimit
        
        # estimate that the error on masked noise occ has same fractional error as the fractional error on the noise occ
        noiseocc_masked_err = [noiseocc_masked*noiseocc_err_frac[0], noiseocc_masked*noiseocc_err_frac[1]]
    
    elif len(gids_hit)>=noise_cut:  
        # use ml clustering to mask the noisy pixels
        totalnoisy, gids_pids_masked, gids_pids_not_masked, masked_gps = ml_masking(gids_hit,pids_hit,noise_cut)
        
        noiseocc_masked = (len(gids_pids_not_masked)/2+n_bad_trains*2)/(1024*n_wf)
        if noiseocc_masked==0: noiseocc_masked = senselimit
        
        # estimate that the error on masked noise occ has same fractional error as the fractional error on the noise occ
        noiseocc_masked_err = [noiseocc_masked*noiseocc_err_frac[0], noiseocc_masked*noiseocc_err_frac[1]]
        
        # use the gids and pids of train 0 of trains of length to get correct number of totalnoisy
        if len(gids_lentwo)>1:
            totalnoisy = 0
            totalnoisy, gids_pids_masked, gids_pids_not_masked, masked_gps = ml_masking(gids_lentwo,pids_lentwo,noise_cut)

    # make sure lower error bar doesn't go below sense limit
    if (noiseocc - noiseocc_err[0]) < senselimit: noiseocc_err[0] = noiseocc - senselimit
    if (noiseocc_masked - noiseocc_masked_err[0]) < senselimit: noiseocc_masked_err[0] = noiseocc_masked - senselimit

    if verbose:
        print("*"*60)
        print(f"  Processed {n_wf:.1e} waveforms, found {n_bad_trains} bad trains.")
        print(f"  Average number of trains per waveform: {n_trains/n_wf}")
        print(f"  Number of triggers = {n_wf:.1e} and number of hits = {n_hits}")
        print(f"  Maximum number of trains in waveform: {max_trains}")
        if n_hits!=0: 
            print(f"  Number of hit events with  1 train  = {n_one_events:3d}, {(n_one_events/(n_wf-n_zero_events))*100:5.2f}%")
            print(f"  Number of hit events with  2 trains = {n_two_events:3d}, {(n_two_events/(n_wf-n_zero_events))*100:5.2f}%")
            print(f"  Number of hit events with >2 trains = {n_multi_events:3d}, {(n_multi_events/(n_wf-n_zero_events))*100:5.2f}%")
            print(f"  Number of undecodable hits = {n_bad_trains:3d}, {(n_bad_trains*2/n_hits)*100:5.2f}%")
        print(f"  Noise occ of chip           = {noiseocc:.2e} + { noiseocc_err[1]:.2e} - { noiseocc_err[0]:.2e} [hits per s per pixel]")
        if totalnoisy!=0:
            print(f"  Noise occ of chip with mask = {noiseocc_masked:.2e} + { noiseocc_masked_err[1]:.2e} - {noiseocc_masked_err[0]:.2e} [hits per s per pixel]")
            print(f"  Number of noisy pixels = {totalnoisy}")
        print("*"*60)

    noiseOccMap = np.zeros((32,32),dtype=float)

    if calibration is not None:
        noiseOccMap = np.divide(data_pixels, n_wf*eventTime)

        cmap = plt.cm.get_cmap("viridis").copy()
        cmap.set_under(color='white')

        noiseOccMap[noiseOccMap==0] = np.nan
        plt.figure("Noise occupancy map")
        plt.subplots_adjust(left=-0.1, right=0.8)
        plt.imshow(noiseOccMap.T,cmap=cmap,norm=LogNorm() if np.any(noiseOccMap>0) else None)
        plt.colorbar(pad=0.008,format='%.0e').set_label('Noise occupancy (hits s$^{-1}$)')
        plt.xlabel('Column')
        plt.ylabel('Row')
        plt.title('Noise occupancy map')
        ax = plt.gca()
        plt.text(1.2, 1, f"Triggers: {n_wf:.1e}\nHits: {n_hits}\nNoise occ.: {noiseocc:.2e}\n# noisy pixels: {totalnoisy}", fontsize = 10,horizontalalignment='left',verticalalignment='center',transform=ax.transAxes)
        plot_parameters(pars, x=1.28, y=0.7)
        plt.savefig(fname+"_noiseOccupancymap.png")

    plt.figure("PID vs GID")
    plt.title('PID vs GID')
    plt.subplots_adjust(left=0.1, right=0.75)
    for i in range(max_trains):
        plt.scatter(gids[i], pids[i], s=1, label=f"train #{i}")
    if len(gids_hit)>=noise_cut and totalnoisy!=0 and calibration is None: 
        masked_gps = np.asarray(masked_gps)
        plt.scatter(masked_gps[:,0],masked_gps[:,1],color='black', marker='+', label=f"Noisy CoG")
    plt.xlabel("GID (ns)")
    plt.ylabel("PID (ns)")
    plt.grid(axis='both')
    ax = plt.gca()
    plt.text(1.02, 0.95, f"Triggers: {n_wf:.1e}\nHits: {n_hits}\nNoise occ.: {noiseocc:.2e}", fontsize = 10,horizontalalignment='left',verticalalignment='center',transform=ax.transAxes)
    if ax.get_legend_handles_labels()[0]:
        plt.legend(bbox_to_anchor=(1.01,0.88), loc="upper left", prop={"family":"monospace"})
    plot_parameters(pars,x=1.02,y=0.50)
    pid_gid_xlims = plt.gca().get_xlim()
    pid_gid_ylims = plt.gca().get_ylim()
    plt.savefig(fname+"_pid_vs_gid.png")

    if mask is not None:
        plt.figure("PID vs GID Masked")
        plt.title('PID vs GID Masked')
        plt.subplots_adjust(left=0.1, right=0.75)
        for i in range(max_trains):
            plt.scatter(gids_masked[i], pids_masked[i], s=1, label=f"train #{i}")
        plt.xlabel("GID (ns)")
        plt.ylabel("PID (ns)")
        plt.grid(axis='both')
        ax = plt.gca()
        plt.text(1.02, 0.95, f"Triggers: {n_wf:.1e}\nMasked hits: {n_hits_masked}\nNoise occ.: {noiseocc_masked:.2e}", fontsize = 10,horizontalalignment='left',verticalalignment='center',transform=ax.transAxes)
        if ax.get_legend_handles_labels()[0]:
            plt.legend(bbox_to_anchor=(1.01,0.88), loc="upper left", prop={"family":"monospace"})
        plot_parameters(pars,x=1.02,y=0.50)
        plt.xlim(pid_gid_xlims)
        plt.ylim(pid_gid_ylims)
        plt.savefig(fname+"_pid_vs_gid_masked.png")

        if calibration is not None:
            noiseOccMap_masked = np.divide(data_pixels_masked, n_wf*eventTime)

            cmap = plt.cm.get_cmap("viridis").copy()
            cmap.set_under(color='white')

            noiseOccMap_masked[noiseOccMap_masked<=0] = np.nan
            plt.figure("Noise occupancy map masked")
            plt.subplots_adjust(left=-0.1, right=0.8)
            plt.imshow(noiseOccMap_masked.T,cmap=cmap,norm=LogNorm() if np.any(noiseOccMap_masked>0) else None)
            plt.colorbar(pad=0.008,format='%.0e').set_label('Noise occupancy (hits s$^{-1}$)')
            plt.xlabel('Column')
            plt.ylabel('Row')
            plt.title('Noise occupancy map masked')
            ax = plt.gca()
            plt.text(1.2, 1, f"Triggers: {n_wf:.1e}\nHits: {n_hits_masked}\nNoise occ.: {noiseocc_masked:.2e}\n# noisy pixels: {totalnoisy}", fontsize = 10,horizontalalignment='left',verticalalignment='center',transform=ax.transAxes)
            plot_parameters(pars, x=1.28, y=0.7)
            plt.savefig(fname+"_noiseOccupancymap_masked.png")

    noiseocc_err = np.array(noiseocc_err)
    noiseocc_masked_err = np.array(noiseocc_masked_err)
    if n_hits>0:
        fraction_of_bad_trains = 100.*n_bad_trains*2/n_hits
    else:
        fraction_of_bad_trains = 0
    np.savez(fname+"_analyzed.npz",noiseocc=noiseocc,noiseocc_err=noiseocc_err, \
                                   noiseocc_masked=noiseocc_masked,noiseocc_masked_err=noiseocc_masked_err, \
                                   totalnoisy=totalnoisy,noisemap=noiseOccMap, \
                                   bad_train_fraction=fraction_of_bad_trains)
    return True

if __name__=="__main__":
    parser = argparse.ArgumentParser("Fake hit-rate analysis.",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("file", help="npy or json file created by fhr.py or directory containing such files.")
    parser.add_argument('--outdir' , default="./plots", help="Directory with output files")
    parser.add_argument('-q', '--quiet', action='store_true', help="Do not display plots.")
    parser.add_argument('--decoding-calib', '--calibration', help="Path to decoding calibration file. Also take the falling edge file and assume the name is the same except for ending with '_falling.npy'")
    parser.add_argument('--noise-cut',default=10, type=int, help="The cut on the number of hits above which a pixel is masked.")
    parser.add_argument('--mask', help="Path to the masking file that contains the pixels to be masked. Mask file contains the pixels to be masked in 'col, row' format. File can either be .txt or .npy.", default=None)
    args = parser.parse_args()

    if '.npy' in args.file:
        analyse_fhr(args.file, args.file.replace('.npy','.json'),args.decoding_calib,args.outdir,args.noise_cut,args.mask)
    elif '.json' in args.file:
        analyse_fhr(args.file.replace('.json','.npy'),args.file,args.decoding_calib,args.outdir,args.noise_cut,args.mask)
    else:
        if '*' not in args.file: args.file+='*.npy'
        print("Processing all file matching pattern ", args.file)
        for f in tqdm(glob.glob(args.file),desc="Processing file"):
            if '.npy' in f and "thr" not in f.split("/")[-1]:
                analyse_fhr(f, f.replace('.npy','.json'),args.decoding_calib,args.outdir,args.noise_cut,args.mask,verbose=False)
                plt.close('all')

    if not args.quiet:
        plt.show()
