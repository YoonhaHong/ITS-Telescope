#!/usr/bin/env python3

import argparse, json
import glob
import numpy as np
from matplotlib import pyplot as plt
from scipy.optimize import curve_fit
from tqdm import tqdm
import os
from pathlib import Path
from mlr1daqboard import dpts_decoder as decoder
from plotting_utils import plot_parameters
from matplotlib.patches import Rectangle

def gaus(x,a,x0,sigma):
    return a*np.exp(-(x-x0)**2/(2*sigma**2))

def scurve_fit(steps, ninj):
    dvs=sorted(steps.keys())
    m=0
    s=0
    den=0
    for dv1,dv2 in zip(dvs[:-1],dvs[1:]):
        ddv=dv2-dv1
        mdv=0.5*(dv2+dv1)
        n1=1.0*steps[dv1]/ninj
        n2=1.0*steps[dv2]/ninj
        dn=n2-n1
        den+=dn/ddv
        m+=mdv*dn/ddv
        s+=mdv**2*dn/ddv/ddv
    if den>0:
        if s>m*m:
            s=(s-m*m)**0.5
        m/=den
        s/=den
    return m,s


def analyse_threshold_scan(npyfile,jsonfile,calibration,outdir,xlim,mask,pixel=None,s_curve_dump=False,verbose=True):
    if not os.path.exists(outdir): os.makedirs(outdir)
    fname = os.path.join(outdir,Path(npyfile).stem)

    with open(jsonfile) as jf:
        pars = json.load(jf)
    if type(calibration)==str:
        calibration=np.load(calibration)

    if mask is not None:
        mask = np.loadtxt(mask)
        if mask.shape==(2,):
            mask = np.array([mask])
        if verbose:
            print("Using a mask:")
            print(mask)

    data_zs = np.load(npyfile)
    data = np.zeros((32,32,len(pars["vsteps"])), dtype=int)
    n_bad_trains = 0
    n_trains = 0
    n_wf = 0
    n_neigh = 0
    tot_vs_vh = []
    for iv,vh in enumerate(tqdm(pars["vsteps"], desc="Converting data",leave=verbose)):
        for ir,r in enumerate(pars["rows"]):
            for ic,c in enumerate(pars["cols"]):
                if mask is not None and ([c,r] == mask).all(axis = 1).any():
                    continue
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
                    if len(trains)==2:
                        tot_vs_vh.append([vh, (trains[1][0]-trains[0][0])*1e9])
                    n_bad_trains += len(bad_trains)
                    n_trains += len(trains)
                    n_wf += 1
    if verbose: 
        print(f"Processed {n_wf} waveforms, found {n_bad_trains} bad edge trains.")
        print(f"Average number of trains per waveform: {n_trains/n_wf}")
        if n_neigh: print(f"In {n_neigh} cases pixel not found in waveform but it neighbour was (possible decoding errors).")

    thrs = []
    noise = []
    thrmap=np.zeros((32,32))
    noisemap=np.zeros((32,32))

    npix = len(pars["rows"])*len(pars["cols"])

    plt.figure("scurve")
    for r in pars["rows"]:
        for c in pars["cols"]:
            if mask is not None and ([c,r] == mask).all(axis = 1).any():
                continue
            m,s = scurve_fit({pars["vsteps"][i]:data[c,r,i] for i in range(len(pars["vsteps"]))}, pars["ninj"])
            plt.plot(pars["vsteps"], data[c,r,:], color='tab:red', alpha=0.1, linewidth=1)#, \
                # label=f"{c}-{r}: Thr: {m:.1f}, Noise: {s:.1f}")
            thrs.append(m)
            noise.append(s)
            thrmap[r,c] = m
            noisemap[r,c] = s
    if pixel:
        c=pixel[0]
        r=pixel[1]
        plt.plot(pars["vsteps"], data[c, r,:], color='tab:blue', alpha=1, linewidth=2, \
            label=f"c:{c}-r:{r}: Thr: {thrmap[r,c]:.1f}, Noise: {noisemap[r,c]:.1f}")

    if s_curve_dump:
        non_zero_thrmap = np.copy(thrmap)
        non_zero_thrmap[non_zero_thrmap<=0] = np.nan
        min_pixel = np.unravel_index(np.nanargmin(non_zero_thrmap,axis=None), non_zero_thrmap.shape)
        max_pixel = np.unravel_index(np.nanargmax(non_zero_thrmap,axis=None), non_zero_thrmap.shape)
        med_pixel = np.argwhere(non_zero_thrmap == np.nanpercentile(non_zero_thrmap, 50, method='nearest'))
        
        non_zero_noisemap = np.copy(noisemap)
        non_zero_noisemap[non_zero_noisemap<=0] = np.nan
        min_noise = np.unravel_index(np.nanargmin(non_zero_noisemap,axis=None), non_zero_noisemap.shape)
        max_noise = np.unravel_index(np.nanargmax(non_zero_noisemap,axis=None), non_zero_noisemap.shape)
        med_noise = np.argwhere(non_zero_noisemap == np.nanpercentile(non_zero_noisemap, 50, method='nearest'))
        
        plt.plot(pars["vsteps"], data[min_pixel[1], min_pixel[0],:], color='tab:brown', alpha=1, linewidth=2, \
            label=f"Min thr: Thr: {thrmap[min_pixel]:.1f}, Noise: {noisemap[min_pixel]:.1f}")
        plt.plot(pars["vsteps"], data[med_pixel[0][1], med_pixel[0][0],:], color='tab:green', alpha=1, linewidth=2, \
            label=f"Med thr: Thr: {thrmap[med_pixel[0][0],med_pixel[0][1]]:.1f}, Noise: {noisemap[med_pixel[0][0],med_pixel[0][1]]:.1f}")
        plt.plot(pars["vsteps"], data[max_pixel[1], max_pixel[0],:], color='tab:orange', alpha=1, linewidth=2, \
            label=f"Max thr: Thr: {thrmap[max_pixel]:.1f}, Noise: {noisemap[max_pixel]:.1f}")
        plt.plot(pars["vsteps"], data[max_noise[1], max_noise[0],:], color='tab:purple', alpha=1, linewidth=2, \
            label=f"Max noise: Thr: {thrmap[max_noise]:.1f}, Noise: {noisemap[max_noise]:.1f}")
        plt.legend(loc="upper left")
        
        # dump the s-curves of all the pixels
        s_curve_dump = {}
        x = [int(z) for z in pars["vsteps"]]
        s_curve_dump['all'] = {}
        for r in pars["rows"]:
            for c in pars["cols"]:
                if (r==min_pixel[0] and c==min_pixel[1]) or (r==med_pixel[0][0] and c==med_pixel[0][1]) or (r==max_pixel[0] and c==max_pixel[1]) or (r==max_noise[0] and c==max_noise[1]): continue
                y = [int(z) for z in data[c,r,:]]
                s_curve_dump['all'][f'{r},{c}'] = list(zip(x,y))
        
        # flag the pixels with the lowest, average and highest threshold and noise
        y = [int(z) for z in data[min_pixel[1],min_pixel[0],:]]
        s_curve_dump["lowest"] = list(zip(x,y))
        y = [int(z) for z in data[med_pixel[0][1],med_pixel[0][0],:]]
        s_curve_dump["average"] = list(zip(x,y))
        y = [int(z) for z in data[max_pixel[1],max_pixel[0],:]]
        s_curve_dump["highest"] = list(zip(x,y))
        y = [int(z) for z in data[max_noise[1],max_noise[0],:]]
        s_curve_dump["highest noise"] = list(zip(x,y))
        s_curve_dump["thr"] = {}
        s_curve_dump["thr"]["lowest"] = (thrmap[min_pixel], noisemap[min_pixel])
        s_curve_dump["thr"]["average"] = (thrmap[med_pixel[0][0],med_pixel[0][1]], noisemap[med_pixel[0][0],med_pixel[0][1]])
        s_curve_dump["thr"]["highest"] = (thrmap[max_pixel], noisemap[max_pixel])
        s_curve_dump["noise"] = {}
        s_curve_dump["noise"]["lowest"] = (thrmap[min_noise], noisemap[min_noise])
        s_curve_dump["noise"]["average"] = (thrmap[med_noise[0][0],med_noise[0][1]], noisemap[med_noise[0][0],med_noise[0][1]])
        s_curve_dump["noise"]["highest"] = (thrmap[max_noise], noisemap[max_noise])

        with open(fname+"_s_curve_dump.json", 'w') as f:
            json.dump(s_curve_dump, f, indent=4)

    plt.xlabel("Injected charge (e$^-$)")
    plt.ylabel("# hits")
    plt.title(f"S-curve measurement ({npix} pixels)")
    if pixel: plt.legend(loc="upper left")
    plt.xlim(0,xlim if xlim else pars["vmax"])
    plt.ylim(0,pars["ninj"]+1)
    plot_parameters(pars)
    plt.savefig(fname+"_scurve.png")

    nbins = 50

    xmax = xlim if xlim else pars["vmax"]
    plt.figure("threshold")
    plt.xlabel('Threshold (e$^-$)')
    plt.ylabel(f'# pixels / ({xmax/nbins:.1f} e$^-$)')
    plt.title(f'Threshold distribution ({npix} pixels)')
    hist,bin_edges,_ = plt.hist(thrs,range=(0,xmax), bins=nbins, \
        label=f"Mean: {np.mean(thrs):5.1f} e$^-$\nRMS:  {np.std(thrs):5.1f} e$^-$")
    bin_mid = (bin_edges[:-1] + bin_edges[1:])/2
    try:
        popt,pcov = curve_fit(gaus, bin_mid, hist, [10,np.mean(thrs),np.std(thrs)])
        perr = np.sqrt(np.diag(pcov))
        plt.plot(np.arange(0,xmax,xmax/nbins/10),gaus(np.arange(0,xmax,xmax/nbins/10),*popt), \
            label=f'$\mu$:    {popt[1]:5.1f}±{perr[1]:5.1f} e$^-$\n$\sigma$:    {popt[2]:5.1f}±{perr[2]:5.1f} e$^-$')
    except Exception as e:
        if verbose: print("Fitting error", e)
    plt.legend(loc="upper right", prop={"family":"monospace"})
    plt.xlim(0,xmax)
    plot_parameters(pars)
    plt.savefig(fname+"_threshold.png")

    xmax = (xlim if xlim else pars["vmax"])*0.1
    plt.figure("noise")
    plt.xlabel('S-curve fit noise (e$^-$)')
    plt.ylabel(f'# pixels / ({xmax/nbins:.1f} e$^-$)')
    plt.title(f'Temporal noise distribution ({npix} pixels)')
    hist,bin_edges,_ = plt.hist(noise,range=(0,xmax), bins=nbins, \
        label=f"Mean: {np.mean(noise):5.1f} e$^-$\nRMS:  {np.std(noise):5.1f} e$^-$")
    bin_mid = (bin_edges[:-1] + bin_edges[1:])/2
    try:
        popt,pcov = curve_fit(gaus, bin_mid, hist, [10,np.mean(noise),np.std(noise)])
        perr = np.sqrt(np.diag(pcov))
        plt.plot(np.arange(0,xmax,xmax/nbins/10),gaus(np.arange(0,xmax,xmax/nbins/10),*popt), \
            label=f'$\mu$:    {popt[1]:5.1f}±{perr[1]:5.1f} e$^-$\n$\sigma$:    {popt[2]:5.1f}±{perr[2]:5.1f} e$^-$')
    except Exception as e:
        if verbose: print("Fitting error", e)
    plt.legend(loc="upper right", prop={"family":"monospace"})
    plt.xlim(0,xmax)
    plot_parameters(pars)
    plt.savefig(fname+"_noise.png")

    cmap = plt.cm.viridis.copy()
    cmap.set_under(color='white')

    plt.figure("Threshold map")
    thrmap[thrmap==0] = np.nan
    plt.subplots_adjust(left=0.008, right=0.78)
    plt.imshow(thrmap,cmap=cmap)
    if pixel:
        plt.gca().add_patch(Rectangle((pixel[0]-.5, pixel[1]-.5), 1, 1, edgecolor="red", facecolor="none"))
    plt.colorbar(pad=0.007).set_label('Threshold (e$^-$)')
    plt.xlabel('Column')
    plt.ylabel('Row')
    plt.title('Threshold map')
    plot_parameters(pars, x=1.23, y=0.7)
    plt.savefig(fname+"_thrmap.png")
    
    plt.figure("Noise map")
    noisemap[noisemap==0] = np.nan
    plt.subplots_adjust(left=0.008, right=0.78)
    plt.imshow(noisemap,cmap=cmap)
    if pixel:
        plt.gca().add_patch(Rectangle((pixel[0]-.5, pixel[1]-.5), 1, 1, edgecolor="red", facecolor="none"))
    plt.colorbar(pad=0.007).set_label('Noise (e$^-$)')
    plt.xlabel('Column')
    plt.ylabel('Row')
    plt.title('Noise map')
    plot_parameters(pars, x=1.23, y=0.7)
    plt.savefig(fname+"_noisemap.png")

    xmax = xlim if xlim else pars["vmax"]
    plt.figure("TOT vs VH")
    plt.subplots_adjust(left=0.13, right=0.8)
    plt.scatter([x for x,y in tot_vs_vh], [y for x,y in tot_vs_vh], alpha=0.1)
    plt.xlabel("VH (mV)")
    plt.ylabel("TOT (ns)")
    plt.xlim(0,xmax)
    plt.grid(axis='both')
    plot_parameters(pars, x=1.01, y=0.7)
    plt.savefig(fname+"_tot_vs_vh.png")

    np.savez(fname+"_analyzed.npz",thresholds=thrmap,noise=noisemap)

    if not verbose:
        plt.close('all')


if __name__=="__main__":
    parser = argparse.ArgumentParser("Threshold analysis.",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("file", help="npy or json file created by dpts_threshold.py or directory containing such files.")
    parser.add_argument('--outdir' , default="./plots", help="Directory with output files")
    parser.add_argument('--xlim', default=0, type=int, help="X axis limit")
    parser.add_argument('-q', '--quiet', action='store_true', help="Do not display plots.")
    parser.add_argument('--decoding-calib', '--calibration', default=None, help="Path to decoding calibration file.")
    parser.add_argument('--pixel', default=None, nargs=2, type=int, help="Highlight one pixel in the s-curves and matrices.")
    parser.add_argument('-s', '--s-curve-dump', action='store_true', help="Dump the s-curves to a json file. Saves all pixels and also flags the pixels with the lowest, average and highest threshold and noise.")    
    parser.add_argument('-m','--mask', help="Path to the masking file that contains the rows to be masked. Mask file contains the rows to be masked in 'row\n' format. File has to be be .txt", default=None)
    args = parser.parse_args()

    if '.npy' in args.file:
        analyse_threshold_scan(args.file, args.file.replace('.npy','.json'),args.decoding_calib,args.outdir,args.xlim,args.mask,args.pixel,args.s_curve_dump)
    elif '.json' in args.file:
        analyse_threshold_scan(args.file.replace('.json','.npy'),args.file,args.decoding_calib,args.outdir,args.xlim,args.mask,args.pixel,args.s_curve_dump)
    else:
        if '*' not in args.file: args.file+='*.npy'
        print("Processing all file matching pattern ", args.file)
        for f in tqdm(glob.glob(args.file),desc="Processing file"):
            if '.npy' in f and "fhr" not in f.split("/")[-1]:
                analyse_threshold_scan(f, f.replace('.npy','.json'),args.decoding_calib,args.outdir,args.xlim,args.mask,args.pixel,args.s_curve_dump,verbose=False)
                plt.close('all')

    if not args.quiet:
        plt.show()
