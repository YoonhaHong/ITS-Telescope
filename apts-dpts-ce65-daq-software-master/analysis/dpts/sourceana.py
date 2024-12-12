#!/usr/bin/env python3

import glob
import argparse, json
import numpy as np
from matplotlib import pyplot as plt
from tqdm import tqdm
import sys, os
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from plotting_utils import plot_parameters
from scipy.optimize import curve_fit
from matplotlib.ticker import FormatStrFormatter

# Non-liner calibration fit function:
# ToT = a*VH + b - c/(VH-d)
# solved for VH

def ToT_to_VH(a,b,c,d,ToT):
    return (-(b-ToT-d*a)+np.sqrt((b-ToT-d*a)**2 - 4*a*(- b*d + d*ToT - c)))/(2*a)

# plots:
# 1. hit multiplicity
# 2. pixel per event
# 3. hitmap
# 5. comparison between uncalibrated and calibrated spectrum

def gaus_py(x,a,x0,sigma):
    return a*np.exp(-(x-x0)**2/(2*sigma**2))

def analyse_fe55(npyfile,jsonfile,xmax,nbin,outdir,calToT,calToTlin,pixel,verbose=True):
    if not os.path.exists(outdir): os.makedirs(outdir)
    fname = os.path.join(outdir,Path(npyfile).stem)

    with open(jsonfile) as jf:
        pars = json.load(jf)

    if verbose:
        if pixel:
            print(f"Using only pixel c:{pixel[0]} r:{pixel[1]}...")
        else:
            print("Using full matrix...")

    if calToTlin:
        if verbose: print(f"Loading linear calibration file: {calToTlin}")
        calToTMap=np.load(calToTlin)
    elif calToT:
        if verbose: print(f"Loading non-linear calibration file: {calToT}")
        calToTload=np.load(calToT)
        calToTMap=calToTload['tot_params']
    else:
        print("Please provide a calibration file (non linear or linear)")
        return False
            
    if "interrupted" in pars:
        print("The scan was interrupted: analysis not supported.", pars['interrupted'])
        return False

    data = np.load(npyfile)

    if pixel:
        _, counts = np.unique(data[:,0], return_counts=True)
        if verbose: 
            print(f"Maximum hit multiplicity: {np.max(counts)}")
            print("Using only single pixel cluster")
        mult_mask=np.repeat(counts, counts)
        data=data[(data[:,1]==pixel[0]) & (data[:,2]==pixel[1]) & (mult_mask==1)]

    nPixelPerEvent = []
    n_pixel = 1
    tot_raw = []
    tot_map = [[[] for i in range(32)] for i in range(32)]
    hitmap=np.zeros((32,32))
    
    # read data, accept only ToT from single pixel event
    # data is a list for each hit of the form [event number, col, row, rising edge, falling edge]
    for hit in tqdm(range(len(data)),desc="Converting data",leave=verbose):
        if ( hit>0 ):
            if ( data[hit][0] == data[hit-1][0] ):
                n_pixel+=1
            # single pixel cluster
            elif ( data[hit][0] != data[hit-1][0] and n_pixel==1 ):
                nPixelPerEvent.append(n_pixel)
                tot_raw.append((data[hit-1][4]-data[hit-1][3])*1e6) # ToT(us)
                tot_map[int(data[hit-1][2])][int(data[hit-1][1])].append(tot_raw[-1])
                hitmap[int(data[hit-1][2]),int(data[hit-1][1])]+=1
            # multiple pixel cluster
            elif( data[hit][0] != data[hit-1][0]):
                nPixelPerEvent.append(n_pixel)
                n_pixel=1

    # keep last event if n_pixel == 1
    if (data[hit][0] != data[hit-1][0] ):
        tot_raw.append((data[hit][4]-data[hit][3])*1e6)
        tot_map[int(data[hit][2])][int(data[hit][1])].append(tot_raw[-1])
        hitmap[int(data[hit][2]),int(data[hit][1])]+=1
    nPixelPerEvent.append(n_pixel)
    
    # define noise cut based on hit multiplicity per pixel
    HitMultiplicity = np.ravel(hitmap)
    HitMultiplicity = HitMultiplicity[HitMultiplicity>0]
    x_max = np.mean(HitMultiplicity) * 2
    x_min = np.mean(HitMultiplicity) * 0.4
    nbins = 80
    plt.figure("Hit multiplicity per pixel")
    plt.title("Hit multiplicity per pixel" + (f" (pixel c:{pixel[0]} r:{pixel[1]})" if pixel else ""))
    plt.subplots_adjust(left=0.13, right=0.8)
    hist, bin_edges,_ = plt.hist(HitMultiplicity,bins=nbins,range=(x_min,x_max),color='darkblue', label="Entries: "+str(len(HitMultiplicity)))
    bin_mid = (bin_edges[:-1] + bin_edges[1:])/2
    try:
        popt,pcov = curve_fit(gaus_py, bin_mid, hist, [100,np.mean(HitMultiplicity),np.std(HitMultiplicity)], bounds=[[-np.inf, -np.inf, 0], np.inf])
        plt.plot(np.arange(x_min,x_max,x_max/nbins/10),gaus_py(np.arange(x_min,x_max,x_max/nbins/10),*popt),color='tab:orange', \
            label=f'$\mu$:    {popt[1]:5.1f}\n$\sigma$:    {popt[2]:5.1f}')
        noise_cut = popt[1] + 5*popt[2]
        plt.axvline(x = noise_cut, color = 'r')
        if verbose:
            print(f"Noise cut = {noise_cut}")
    except Exception as e:
        if verbose: print("Fitting error", e)
    plt.xlabel("Hit multiplicity")
    plt.ylabel("Counts")
    plt.xlim([np.mean(HitMultiplicity)*0.4,np.mean(HitMultiplicity)*2.1])
    plt.grid(axis='both')
    plt.legend(loc="upper right")
    plt.text(1.02*noise_cut, 0.15*np.max(hist), f"{noise_cut:5.0f}",color='red')
    plot_parameters(pars, x=1.01)
    plt.savefig(fname+"_hit_multiplicity" + (f"_pixel{pixel[0]}-{pixel[1]}" if pixel else "") + ".png")

    # ToT calibration and evaluation of mean m and q for the final plot
    npt = 0
    mean_m = 0
    mean_q = 0
    mean_c = 0
    mean_d = 0
    tot = []
    tot_calibrated = []
    for row in range(32):
        for col in range(32):
            if calToTlin:
                if (hitmap[row][col]<=noise_cut and np.isfinite(calToTMap[row][col][0]) and np.isfinite(calToTMap[row][col][1]) and row not in [0, 31] and col not in [0, 31]):
                    m = calToTMap[row][col][0]
                    q = calToTMap[row][col][1]
                    npt+=1
                    mean_m+=m
                    mean_q+=q
                    for k in range(len(tot_map[row][col])):
                        tot.append(tot_map[row][col][k])
                        tot_calibrated.append((tot_map[row][col][k]*1e3-q)/m) #the ToT has to be in ns
            if calToT:
                if (hitmap[row][col]<=noise_cut and np.isfinite(calToTMap[row][col][0]) and np.isfinite(calToTMap[row][col][1]) and np.isfinite(calToTMap[row][col][2]) and np.isfinite(calToTMap[row][col][3])\
                    and row not in [0, 31] and col not in [0, 31]):
                    a = calToTMap[row][col][0]
                    b = calToTMap[row][col][1]
                    c = calToTMap[row][col][2]
                    d = calToTMap[row][col][3]
                    npt+=1
                    mean_m+=a
                    mean_q+=b
                    mean_c+=c
                    mean_d+=d
                    for k in range(len(tot_map[row][col])):
                        tot.append(tot_map[row][col][k])
                        tot_calibrated.append(ToT_to_VH(a,b,c,d,tot_map[row][col][k])) #the ToT has to be in us
    mean_m = mean_m/npt
    mean_q = mean_q/npt
    mean_c = mean_c/npt
    mean_d = mean_d/npt
    if calToT:
        mean_m = mean_m*1e3
        mean_q = mean_q*1e3
    print("mean_m, mean_q = ",mean_m, mean_q)
    print("mean_c, mean_d = ",mean_c, mean_d)

    plt.figure("Pixel per event")
    plt.title("Pixel per event" + (f" (pixel c:{pixel[0]} r:{pixel[1]})" if pixel else ""))
    plt.subplots_adjust(left=0.13, right=0.8)
    n, bins, patches = plt.hist(nPixelPerEvent,bins=6,label="Entries: "+str(len(nPixelPerEvent)),color='darkblue',range=(-0.5,5.5),width=0.95)
    plt.xlabel("# pixel")
    plt.ylabel("Counts")
    plt.grid(axis='both')
    plt.legend(loc="upper right")
    plt.gca().set_yscale('log')
    xticks = [(bins[idx+1] + value)/2 for idx, value in enumerate(bins[:-1])]
    for idx, value in enumerate(n):
        if value > 0:
            plt.text(xticks[idx], value+1000,f"{value/len(nPixelPerEvent)*100:5.1f} %", ha='center')
    plot_parameters(pars, x=1.01)
    plt.savefig(fname+"_pixel_per_event" + (f"_pixel{pixel[0]}-{pixel[1]}" if pixel else "") + ".png")

    hitmap[hitmap==0] = np.nan
    plt.figure("Hitmap")
    plt.subplots_adjust(left=0.01, right=0.80)
    plt.imshow(hitmap)
    plt.colorbar(pad=0.015).ax.set_title('Hits')
    plt.xlabel('Column')
    plt.ylabel('Row')
    plt.title('Hitmap one pixel clusters' + (f" (pixel c:{pixel[0]} r:{pixel[1]})" if pixel else ""))
    plot_parameters(pars, x=1.23, y=0.7)
    plt.savefig(fname+"_hitmapOnePixelClusters" + (f"_pixel{pixel[0]}-{pixel[1]}" if pixel else "") + ".png")

    hitmap[hitmap>noise_cut] = np.nan
    hitmap[(0,31),:] = np.nan
    hitmap[:,(0,31)] = np.nan
    plt.figure("Hitmap with cut applied")
    plt.subplots_adjust(left=0.01, right=0.80)
    plt.imshow(hitmap)
    plt.colorbar(pad=0.015).ax.set_title('Hits')
    plt.xlabel('Column')
    plt.ylabel('Row')
    plt.title('Hitmap one pixel clusters with cut applied' + (f" (pixel c:{pixel[0]} r:{pixel[1]})" if pixel else ""))
    plot_parameters(pars, x=1.23, y=0.7)
    plt.savefig(fname+"_hitmapOnePixelClustersCut" + (f"_pixel{pixel[0]}-{pixel[1]}" if pixel else "") + ".png")

#%% FINAL PLOT
    # calibrated spectrum with fit and uncalibrated spectrum
    color_uncalibrated = 'tab:blue'
    color_calibrated = 'tab:orange'
    fig,ax1 = plt.subplots(figsize=(8,5))
    plt.subplots_adjust(left=0.1,right=0.8,top=0.90)
    ax2 = ax1.twiny()

    hist,bin_edges,_ = ax1.hist(tot_calibrated,nbin,label="Calibrated, entries: "+str(len(tot_calibrated)),color=color_calibrated,edgecolor=color_calibrated,range=(0,xmax),histtype='stepfilled',alpha=0.5)
    ax1.set_xlabel("Calibrated ToT (mV)")
    ax1.set_ylabel("Counts")
    ax1.grid(axis='both')
    ax1.set_xlim(-100,xmax+100)

    ax1.xaxis.label.set_color(color_calibrated)
    for obj in ax1.xaxis.get_ticklines():
        obj.set_color(color_calibrated)
    for obj in ax1.xaxis.get_ticklabels():
        obj.set_color(color_calibrated)

    ax2.hist(tot,nbin,label="Uncalibrated, entries: "+str(len(tot)),range=(0,(xmax*mean_m+mean_q)/1000),edgecolor=color_uncalibrated,histtype='stepfilled', alpha=0.5)
    ax2.set_xlabel("ToT ($\mu$s)")
    ax2.set_ylabel("Counts")
    ax2.grid(axis='both')
    ax2.set_xlim((-100*mean_m+mean_q)/1000,((xmax+100)*mean_m+mean_q)/1000)
    ax2.set_axisbelow(True)

    x_ticks = ((np.arange(0,xmax+250,250))*mean_m+mean_q)/1000
    ax2.set_xticks(x_ticks, x_ticks)
    ax2.xaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    ax2.xaxis.label.set_color(color_uncalibrated)
    for obj in ax2.xaxis.get_ticklines():
        obj.set_color(color_uncalibrated)
    for obj in ax2.xaxis.get_ticklabels():
        obj.set_color(color_uncalibrated)
    ax1.set_facecolor("none")
    ax2.set_facecolor("none")
    ax2.set_zorder(0)
    ax1.set_zorder(10)

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1[:1]+h2+h1[1:],l1[:1]+l2+l1[1:],loc='upper left',prop={"size":11})
    plot_parameters(pars, x=1.02)
    if pixel:
        plt.title(f"Spectrum using only pixel c:{pixel[0]} r:{pixel[1]}")
    else:
        plt.title("Spectrum for the whole matrix")
    plt.savefig(fname+"_ToTRawSpectrum_CalibratedSpectrum" + (f"_pixel{pixel[0]}-{pixel[1]}" if pixel else "") + ".png")

    tot_calibrated=np.array(tot_calibrated)
    tot=np.array(tot)
    np.savez(fname+"_sourceana_analyzed" + (f"_pixel{pixel[0]}-{pixel[1]}" if pixel else "") + ".npz",calibratedToT=tot_calibrated,uncalibratedToT=tot)
    
    return True

if __name__=="__main__":
    parser = argparse.ArgumentParser("Source data analysis.",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("file", help="npy or json file created by source_decoder.py or directory containing such files.")
    parser.add_argument('--calToT', help=".npz file for the ToT non-linear calibration created by toatotana.py")
    parser.add_argument('--calToTlin', help=".npy file for the ToT linear calibration created by totcalana.py")
    parser.add_argument('--xmax' , type=int, default=2000, help="Maximum for the calibrated ToT x axis in mV.")
    parser.add_argument('--nbin' , type=int, default=280, help="Number of bin for the spectrum histograms.")
    parser.add_argument('--pixel' , type=int, nargs=2, help="Make spectrum with a single pixel only.")
    parser.add_argument('--outdir' , default="./plots", help="Directory with output files")
    parser.add_argument('-q', '--quiet', action='store_true', help="Do not display plots.")
    args = parser.parse_args()
    
    if '.npy' in args.file:
        analyse_fe55(args.file, args.file.replace('.npy','.json'),args.xmax,args.nbin,args.outdir,args.calToT,args.calToTlin,args.pixel)
    elif '.json' in args.file:
        analyse_fe55(args.file.replace('.json','.npy'),args.file,args.xmax,args.nbin,args.outdir,args.calToT,args.calToTlin,args.pixel)
    else:
        if '*' not in args.file: args.file+='*.npy'
        print("Processing all file matching pattern ", args.file)
        for f in tqdm(glob.glob(args.file),desc="Processing file"):
            if '_decoded.npy' in f:
                analyse_fe55(f, f.replace('.npy','.json'),args.xmax,args.nbin,args.outdir,args.calToT,args.calToTlin,args.pixel,verbose=False)
                plt.close('all')

    if not args.quiet:
        plt.show()