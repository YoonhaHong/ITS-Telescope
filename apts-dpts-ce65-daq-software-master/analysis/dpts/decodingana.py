#!/usr/bin/env python3

import argparse, json
import numpy as np
from matplotlib import pyplot as plt
from tqdm import tqdm
import os
from mlr1daqboard import dpts_decoder as decoder
from plotting_utils import plot_parameters

parser = argparse.ArgumentParser("Decoding calibration analysis.",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("file", help=".npy or .json file created by dpts_decoding_calib.py")
parser.add_argument('--outdir' , default="./plots", help="Directory with output files")
parser.add_argument('--xlim', default=0, type=int, help="X axis limit")
parser.add_argument('-q', '--quiet', action='store_true', help="Do not display plots.")
parser.add_argument('--save-calibration', default=None, help="File name of output calibration file.")
parser.add_argument('--verify-calibration', default=None, help="File name of calibration to verify.")
parser.add_argument('--falling-edge', action='store_true', help="Calibrate on falling edge instead of the rising edge.")
parser.add_argument('--gid-scale', default=1., type=float)
parser.add_argument('--pid-scale', default=1., type=float)
parser.add_argument('--show-failures', action='store_true', help="Show the calibration verification failures.")
args = parser.parse_args()

if '.npy' in args.file:
    args.npy = args.file
    args.json = args.file.replace('.npy','.json')
elif '.json' in args.file:
    args.npy = args.file.replace('.json','.npy')
    args.json = args.file
else:
    raise ValueError(f"Unrecognised extension for: {args.file}. Please choose a .npy or .json file.")

if not os.path.exists(args.outdir): os.makedirs(args.outdir)
fname = args.outdir+'/'+args.npy[args.npy.rfind('/')+1:].replace('.npy','')

with open(args.json) as jf:
    pars = json.load(jf)

data_zs = np.load(args.npy)
max_trains = 5
pids = [[] for _ in range(max_trains)]
gids = [[] for _ in range(max_trains)]
t0s  = [[] for _ in range(max_trains)]
bad_t0s = []
n_bad_trains = 0
n_trains = 0
n_wf = 0
calib = [[[] for i in range(32)] for i in range(32)] # only calibrate rising edges pulses
for iv in tqdm(range(len(pars["vsteps"])), desc="Converting data"):
    for ir,r in enumerate(pars["rows"]):
        for ic,c in enumerate(pars["cols"]):
            for inj in range(pars["ninj"]):
                trains,bad_trains = decoder.zs_to_trains(data_zs[ic,ir,iv,inj])
                for i,edges in enumerate(trains):
                    pids[i].append((edges[2]-edges[0])*1e9)
                    gids[i].append((edges[3]-edges[2])*1e9)
                    t0s[i].append(edges[0]*1e9)
                for edges in bad_trains:
                    bad_t0s.append(edges[0]*1e9)
                n_bad_trains += len(bad_trains)
                n_trains += len(trains)
                n_wf += 1
                gps = decoder.trains_to_gid_pid(trains)
                if len(gps)==2: # one rising and one falling edge
                    if args.falling_edge:
                        calib[c][r].append(gps[1]) # take falling
                    else:
                        calib[c][r].append(gps[0]) # take rising
max_trains = next((i for i in range(max_trains) if len(pids[i])==0),5)
print(f"Processed {n_wf} waveforms, found {n_bad_trains} bad edge trains.")
print(f"Average number of trains per waveform: {n_trains/n_wf}")
print(f"Maximum number of trains in waveform: {max_trains}")

n_no_data_pixels = 0
trunc_frac = 0.05 # truncate 5% from both ends
col_row_to_gid_pid = np.full((32,32,2),-np.inf,dtype=np.float32)
for r in pars["rows"]:
    for c in pars["cols"]:
        ntrunc = max(int(len(calib[c][r])*trunc_frac),1) # at least 1 outlier
        if len(calib[c][r])<=2*ntrunc:
            print("WARNING: No data for pixel", c, r)
            n_no_data_pixels += 1
            continue
        col_row_to_gid_pid[c,r,:] = np.mean(sorted(calib[c][r])[ntrunc:-ntrunc],axis=0) # truncate outliers

if n_no_data_pixels!=0: print(f"Number of pixels with no data = {n_no_data_pixels}")

if args.verify_calibration is not None:
    verif_calib = np.load(args.verify_calibration)
    print("Verifying calibration from file", args.verify_calibration)
else:
    verif_calib = col_row_to_gid_pid
verif_calib[:,:,0]*=args.gid_scale
verif_calib[:,:,1]*=args.pid_scale
acc = [0,0]
fails = []
if args.show_failures:
    fail_map = np.zeros((32,32))
    fail_cog = []
for iv in tqdm(range(len(pars["vsteps"])), desc="Verifying calibration",leave=True):
    for ir,r in enumerate(pars["rows"]):
        for ic,c in enumerate(pars["cols"]):
            for inj in range(pars["ninj"]):
                pix = decoder.zs_to_pix(verif_calib,data_zs[ic,ir,iv,inj],falling_edge=args.falling_edge)
                if len(pix)==0: continue
                acc[1]+=1
                if (c,r) not in pix:
                    acc[0]+=1
                    if acc[0]<1000:
                        fails.append(f"({c},{r}): {verif_calib[c,r]*1e9} not found in decoded pixels: {pix}")
                        if args.show_failures:
                            fail_map[r][c] += 1
                            trains,_ = decoder.zs_to_trains(data_zs[ic,ir,iv,inj])
                            gps = decoder.trains_to_gid_pid(trains)
                            if args.falling_edge:
                                fail_cog.append((gps[1]))
                            else:
                                fail_cog.append((gps[0]))
if fails:
    print("\n".join(fails))
    if acc[0]>=1000: print(f"And {acc[0]-1000} more lines like this...")
    print("Decoding fails: ", acc[0], "out of", acc[1])
else:
    print("No decoding errors detected.")

if args.save_calibration:
    np.save(args.save_calibration,col_row_to_gid_pid)
    print("Calibration file saved to:", args.save_calibration)

plt.figure("PID vs GID")
plt.subplots_adjust(left=0.09, right=0.8)
for i in range(max_trains):
    plt.scatter(gids[i], pids[i], s=1, label=f"Train #{i}")
plt.scatter(verif_calib[:,:,0].reshape(1024)*1e9,verif_calib[:,:,1].reshape(1024)*1e9,color='black', marker='+', label=f"CoG")
if args.show_failures:
    for i in range(len(fail_cog)):
        if i==0: plt.scatter(fail_cog[i][0]*1e9,fail_cog[i][1]*1e9,color='red', marker='+', label=f"Fail veri")
        else: plt.scatter(fail_cog[i][0]*1e9,fail_cog[i][1]*1e9, marker='+',color='red')
plt.xlabel("GID (ns)")
plt.ylabel("PID (ns)")
plt.grid(axis='both')
plt.legend(loc='best',bbox_to_anchor=(1.01,1))
plot_parameters(pars,x=1.01,y=0.6)
if args.show_failures: plt.savefig(fname+"_pid_vs_gid_with_fails.png")
else: plt.savefig(fname+"_pid_vs_gid.png")

plt.figure("T0s distribution")
plt.subplots_adjust(left=0.09, right=0.8)
hist,bin_edges = np.histogram(sum(t0s,bad_t0s),'auto')
for i in range(max_trains):
    plt.hist(t0s[i],bin_edges,label=f"Train #{i}")
plt.hist(bad_t0s,bin_edges,label="Bad t0s",color='red')
plt.xlabel("t0 (ns)")
plt.ylabel("a.u.")
plt.gca().set_yscale('log')
plt.legend(loc='best')
plot_parameters(pars,x=1.01,y=0.6)
plt.savefig(fname+"_t0s.png")

if args.show_failures:
    cmap = plt.cm.viridis.copy()
    cmap.set_under(color='white')

    fail_map[fail_map==0] = np.nan
    plt.figure("Decoding fail map")
    plt.title("Decoding fail map")
    plt.subplots_adjust(left=0.1, right=0.8)
    plt.imshow(fail_map,cmap=cmap)
    plt.colorbar(pad=0.007).set_label('Entries')
    plt.xlabel('Column')
    plt.ylabel('Row')
    plot_parameters(pars,x=1.21,y=0.6)
    plt.savefig(fname+"_decoding_fail_map.png")

if not args.quiet: plt.show()
