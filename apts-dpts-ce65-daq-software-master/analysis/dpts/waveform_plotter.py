#!/usr/bin/env python3

import argparse
import os
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def waveform_plotter(args):
    waveform = np.load(args.file)

    if args.outfile == None:
        outfile = os.path.join(args.outdir, Path(args.file).stem + "_waveform_plot")
    else:
        outfile = os.path.join(args.outdir,args.outfile)
    plt.figure(figsize=(10,5))

    assert args.N>=1, "ERROR: N must be 1 or bigger. See help message for details."

    if args.N > 1: #check if more than 1 waveform is grouped together (if yes, npy file needs to be read differently)
        for aq in range (0, len(waveform)-1):
            plt.plot(np.arange(0,len(waveform[aq][0])),waveform[aq][0])
            plt.plot(np.arange(0,len(waveform[aq][1])),waveform[aq][1])
    elif args.N == 1:
            plt.plot(np.arange(0,len(waveform[0])),waveform[0])
            plt.plot(np.arange(0,len(waveform[1])),waveform[1])

    plt.xlabel("Timestanp [a.u.]")
    plt.ylabel("ADC")
    plt.savefig(outfile)
    print("Saved plot to: ", outfile)

    if not args.quiet:
        plt.show()

    print("Thank you for using waveform_plotter.py!")

if __name__=="__main__":
    parser = argparse.ArgumentParser("DPTS waveform plotter",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("file", help ="Waveform file to plot (.npy)")
    parser.add_argument("--outdir", help = "Target file to write plot to", default = "./plots")
    parser.add_argument("--outfile", help = "Name of the target file", default = None)
    parser.add_argument("-N", help = "Number of aquisitions grouped in segmented aquisition (take same value as used in pico_daq.py)", type=int ,default=1)
    parser.add_argument("--quiet", "-q", action='store_true', help="Do not display plots.")

    args = parser.parse_args()

    waveform_plotter(args)
