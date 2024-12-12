#!/usr/bin/env python3

#====================
#
# IMPORTS
#
#====================

import argparse
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mlr1daqboard.dpts_decoder as decoder
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from tqdm import tqdm

#====================
#
# FUNCTIONS
#
#====================

def get_filename_lst(datapath):
    filename_lst = []
    for filename in tqdm(os.listdir(datapath), desc = "Get list of filenames"):
        waveformfile = os.path.join(datapath,filename)
        if os.path.isfile(waveformfile):
            filename_lst.append(waveformfile)
    return filename_lst


def get_trains_from_waveformfile(waveformfile):
    #uncommented lines in this function stress the difference of reading in waveformfiles with lab/ TB setup
    # for TB just one channel of the oscilloscope is needed
    d =np.load(waveformfile)
    #if d.shape[0]==3:
    #    t=d[0,:]*1e-9
    #    p=d[1,:]*1e-3
    #    n=d[2,:]*1e-3
    #if d.shape[0]==2:
    t=np.linspace(0,d.shape[1]*2e-10,d.shape[1],endpoint=False)
    p=d[0,:]#*0.006151574803149607*256
    n=d[1,:]#*0.006151574803149607*256
    trains,bad_trains=decoder.decode(t,p,n, only_pos = True, fix_thresh=30)
    return trains, bad_trains


def get_ToT_from_waveform(waveformfile):
    #just used for uncorreced landau
    trains, bad_trains = get_trains_from_waveformfile(waveformfile)
    if len(trains)==2:
        ToT = trains[1][0]-trains[0][0]
    else:
        ToT =  np.NaN
    return ToT


def wave_ToT_decoding_ana(file, calibfile):
    px_ToT_lst=[]
    data_zs = np.load(file)
    calibration = np.load(calibfile)     
    trains,bad_trains = get_trains_from_waveformfile(file)    
    if calibration is not None:
        pixels = decoder.trains_to_pix(calibration,trains,bad_trains)
    if len(trains)==2 and len(pixels)==1:
        ToT=trains[1][0]-trains[0][0] #calculate ToT
        px_ToT_lst.append((pixels[0],ToT)) #px_ToT_lst=[((col,row),ToT), ...]
    return px_ToT_lst


def get_px_ToT_lst(filename_lst, calibfile):
    #creates pixel-ToT list px_ToT_lst=[((col,row),ToT), ...]
    px_ToT_lst = []
    for f in tqdm(filename_lst, desc = "Decoding files"):
        px_ToT = wave_ToT_decoding_ana(f, calibfile)
        if px_ToT: px_ToT_lst.append(px_ToT)
    return px_ToT_lst


def get_landau_raw(datapath):
    ToT_lst = []
    for filename in tqdm(os.listdir(datapath), desc = "Extract data from files"):
        waveformfile = os.path.join(datapath,filename)
        if os.path.isfile(waveformfile):
            ToT_lst.append(get_ToT_from_waveform(waveformfile))
        else: print("[ERROR]: File not found.")
    return ToT_lst


def get_col_row_ToT(px_ToT_lst, ev, use_decoded_data):
    if (use_decoded_data):
        col = int(px_ToT_lst[ev][0][0])
        row = int(px_ToT_lst[ev][0][1])
        ToT = px_ToT_lst[ev][1]
    else:
        col = px_ToT_lst[ev][0][0][0]
        row = px_ToT_lst[ev][0][0][1]
        ToT = px_ToT_lst[ev][0][1]
    return col, row, ToT


def correct_ToT(ToT, col, row, totcalib, totcalib_nonlin):
    if not (totcalib_nonlin):
        ToT_corr = (ToT*1e9 - totcalib[row][col][1]) / totcalib[row][col][0] #correct ToT linear
    elif (totcalib_nonlin):
        a = totcalib['tot_params'][row][col][0]
        b = totcalib['tot_params'][row][col][1]
        c = totcalib['tot_params'][row][col][2]
        d = totcalib['tot_params'][row][col][3]
        ToT_corr = (-(b-ToT*1e6-d*a)+np.sqrt((b-ToT*1e6-d*a)**2 - 4*a*(- b*d + d*ToT*1e6 - c)))/(2*a) #correct ToT
    else:
        print('[ERROR] Type of ToT calibration not specified!')
        exit()        
    return ToT_corr


def get_corrected_px_ToT_lst(px_ToT_lst, totcalib, totcalib_nonlin, use_decoded_data):
    ToT_lst_corr = []
    px_ToT_lst_corr = []
    for ev in tqdm(range(0, len(px_ToT_lst)), desc = "Correcting ToT for every event"):
        col, row, ToT = get_col_row_ToT(px_ToT_lst, ev, use_decoded_data)
        if not (col == 0 or row == 0 or col == 31 or row ==31): #exclude border pixels
            ToT_corr = correct_ToT(ToT, col, row, totcalib, totcalib_nonlin)
            ToT_lst_corr.append(ToT_corr)
            px_ToT_lst_corr.append([col, row, ToT_corr]) #nan value used to create homogenious shape
    return ToT_lst_corr, px_ToT_lst_corr


def convert_to_electrons(ToT_lst_corr, energycalib):
    #coverts calibrated ToT list (mV) to electrons
    ToT_lst_corr_electrons = []
    energy_corrfac = np.load(energycalib)
    for ToT in ToT_lst_corr:
        ToT_lst_corr_electrons.append((ToT*energy_corrfac))
    return ToT_lst_corr_electrons


def sort_decoded_source_data(decoded_source_data):
    #sorts decoded source data so clusters come evident
    #every line is one event with multiple hits
    sorted=decoded_source_data[decoded_source_data[:,0].argsort(kind="mergesort")]
    unique, indices, counts = np.unique(sorted[:,0], axis=0, return_counts=True, return_index=True)
    stacked=np.hstack((sorted, np.repeat(counts, counts).reshape(-1, 1)))
    max_hits=np.max(counts)
    mask=np.repeat(np.append(indices[1:], -1), max_hits-counts)
    stacked=np.insert(stacked, mask, np.full((stacked.shape[1]), np.nan), axis=0)
    stacked=np.reshape(stacked, (unique.shape[0], max_hits, stacked.shape[1]))
    return stacked


def get_cluster_px_ToT_lst(sorted_decoded_source_data):
    #returns list like [ [(c1, r1), (c2, r2), (c3, r3)], [ToT_1, ToT_2, ToT_3] ], ... ]
    cluster_px_ToT_lst = []
    for event in tqdm(sorted_decoded_source_data, desc="Getting clusters from events"):
        ToTs_in_event = []
        pix_in_event = []
        for hit in event:
            eventnr, col, row, rising_edge, falling_edge = decode_hit(hit)
            if np.isfinite(eventnr):
                ToTs_in_event.append(falling_edge - rising_edge)
                pix_in_event.append((col, row))
        ToTs_in_event = np.array(ToTs_in_event)
        cluster_px_ToT_lst.append([pix_in_event, ToTs_in_event])
    return cluster_px_ToT_lst


def decode_hit(hit):
    #gets information out of hit (e.g a line in decoded source data)
    eventnr = hit[0]
    col = hit[1]
    row = hit[2]
    rising_edge = hit[3]
    falling_edge = hit[4]
    return eventnr, col, row, rising_edge, falling_edge

def correct_cluster_pix_ToT_list(cluster_pix_ToT_list, totcalib, totcalib_nonlin, bordercut):
    #takes cluster_pix_ToT_list and corrects it for nonlinear ToT variations, cuts away clusters with a seedpixel as borderpixel
    cluster_pix_ToT_list_corr = []

    for cl in tqdm(cluster_pix_ToT_list, desc = "Correcting ToT for every cluster, removing borderpixels"):
        corrected_ToTs_in_cluster = []
        pxs_in_cluster = []
        for hitnr in range(0, len(cl[0])):
            col = int(cl[0][hitnr][0])
            row = int(cl[0][hitnr][1])
            ToT = cl[1][hitnr]
            corrected_ToTs_in_cluster.append(correct_ToT(ToT, col, row, totcalib, totcalib_nonlin))
            pxs_in_cluster.append((col, row))
    
        #cut away events where the seedpixel is to close to the border
        seedpix = pxs_in_cluster[np.argmax(corrected_ToTs_in_cluster)]
        spc = seedpix[0] #seed pixel column
        spr = seedpix[1] #seed pixel row
        minc = bordercut - 1 #minimum column
        minr = bordercut - 1 #minimum row
        maxc = 31 - bordercut #maximum column
        maxr = 31 - bordercut #maximum row
        
        if (spc > minc) and (spr > minr) and (spc < maxc) and (spr < maxr):
            cluster_pix_ToT_list_corr.append([pxs_in_cluster, corrected_ToTs_in_cluster])

    return cluster_pix_ToT_list_corr


def get_seedpixel_and_cluster_energy_distribution(cluster_pix_ToT_list_corr, energycalib):
    seedpix_ToTs = []
    cluster_ToT_sums = []

    for cl in tqdm(cluster_pix_ToT_list_corr, desc = "Getting seedpixel energy distribution"):
        corrected_ToTs_in_cluster = []
        for hitnr in range(0, len(cl[0])):
            col = int(cl[0][hitnr][0])
            row = int(cl[0][hitnr][1])
            ToT = cl[1][hitnr]
            corrected_ToTs_in_cluster.append(ToT)

        #get seedpixel and cluster energy
        seedpix_ToTs.append(np.max(corrected_ToTs_in_cluster))
        cluster_ToT_sums.append(np.sum(corrected_ToTs_in_cluster))

    #perform energy_calibration
    seedpix_energies = convert_to_electrons(seedpix_ToTs, energycalib)
    cluster_energies = convert_to_electrons(cluster_ToT_sums, energycalib)

    return seedpix_energies, cluster_energies


#=================
#
# MAIN
#
#=================

if __name__=="__main__":
    parser = argparse.ArgumentParser("Landau plotter")
    parser.add_argument("data", help ="Either directory with dumped waveform files to plot (created by eudaq2/user/ITS3/scripts/DPTSDump.py) or .npy file created by source_decoder.py (set flag correspondingly)")
    parser.add_argument("totcalib", help ="ToT Calibration factor map created by totcalana.py (linear) or toatotana.py (non-linear)")
    parser.add_argument("--calibfile", help ="Calibration file for position decoding (only required if dumped waveformfiles are used as an input)")
    parser.add_argument("--use_decoded_data", action = 'store_true', help = "Use data created by source_decoder.py (required for creating seedpixel distribution)")
    parser.add_argument("--energycalib", help = "Corresponding energy calibration produced by energy_calib.py")
    parser.add_argument('--totcalib_nonlin', action = 'store_true', help= "Interpret the provided totcalib as non-linear function (recommended if corresponding data is available)")
    parser.add_argument("--quiet","-q", action = 'store_true', help= "Do not plot control plots")
    parser.add_argument("--outdir", help = "Target file to write plot to", default = "./plots")
    args = parser.parse_args()

    #load tot-calibration file
    totcalib = np.load(args.totcalib)

    if (args.use_decoded_data):
        print("[INFO] Using decoded source data as input")
        #sort decoded source data to arange all events in a cluster in the same line
        sorted_decoded_data = sort_decoded_source_data(np.load(args.data))
        #get cluster pix ToT list
        cluster_pix_ToT_list = get_cluster_px_ToT_lst(sorted_decoded_data)
        #correct cluster pix ToT list for interpixel ToT variations, cut of borderpix
        cluster_pix_ToT_list_corrected = correct_cluster_pix_ToT_list(cluster_pix_ToT_list, totcalib, args.totcalib_nonlin, 2)
        #extract seedpixel and cluster energies from cluster pix ToT list
        seedpix_energies, cluster_energies = get_seedpixel_and_cluster_energy_distribution(cluster_pix_ToT_list_corrected, args.energycalib)


    else:
        print("[INFO] Using dumped waveforms as input")
        #Convert datapath
        datapath = os.path.join(args.data)
        #Counting files
        filename_lst = get_filename_lst(datapath)
        n_files = len(filename_lst)
        print("[INFO] Found ", n_files, "files in ", args.data)
        #Obtaining ToT list
        ToT_lst = get_landau_raw(datapath)
        #Applying ToT calibration
        px_ToT_lst = get_px_ToT_lst(filename_lst, args.calibfile) #ToT_decoding_ana(datapath, args.calibfile, n_files)
        #Correcting with ToT calibrations
        ToT_lst_corr, px_ToT_lst_corr = get_corrected_px_ToT_lst(px_ToT_lst, totcalib, args.totcalib_nonlin, args.use_decoded_data)
        #Converting to electrons
        if(args.energycalib):
            ToT_lst_corr_electrons = convert_to_electrons(ToT_lst_corr, args.energycalib)

    if not os.path.exists(args.outdir): os.makedirs(args.outdir) 

    #Save data
    print("[INFO] Saving data ...")
    if not (args.use_decoded_data):
        np.savez(os.path.join(args.outdir, "landau_analyzed.npz"), uncorrected=ToT_lst, corrected=ToT_lst_corr, corrected_electrons=ToT_lst_corr_electrons, corrected_electrons_pix=px_ToT_lst_corr)
    elif (args.use_decoded_data):
        np.savez(os.path.join(args.outdir, "landau_analyzed_seedpix.npz"), seedpixel_energies=seedpix_energies)
        np.savez(os.path.join(args.outdir, "landau_analyzed_cluster.npz"), cluster_energies=cluster_energies)

    print("[INFO] Data saved to: ", args.outdir)


#=================
#
#  CONTROL PLOTS
#
#=================

    if not (args.use_decoded_data):
        print("[INFO] Plotting control plots")
        #Plot Landau uncorrected
        plt.hist(ToT_lst, bins = 50, color = 'navy')
        plt.ticklabel_format(axis="x", style="sci", scilimits=(0,0))
        plt.xlabel("ToT (s)")
        plt.ylabel("Entries")
        plt.savefig(args.outdir+"Landau_uncorrected.png",bbox_inches = 'tight', dpi = 600)

    #Plot Landau seedpix vs cluster energy sepctrum
    if args.use_decoded_data:
        plt.figure()
        plt.hist(seedpix_energies, bins = 100, histtype="step", color = 'red', density=True, range=(0,2000), label='Seedpixel energies')
        plt.hist(cluster_energies, bins = 100, histtype="step", color = 'blue', density=True, range=(0,2000), label='Cluster energies')
        plt.xlim([0, 2000])
        plt.xlabel("Energy (e)")
        plt.ylabel("Entries")
        plt.legend()
        plt.savefig(args.outdir+"seedix_vs_cluster_spectrum.png",bbox_inches = 'tight', dpi = 600)

    if not(args.quiet):
        print("[INFO] Showing plots ...")
        plt.show()

    print("[INFO] Program finished!")
