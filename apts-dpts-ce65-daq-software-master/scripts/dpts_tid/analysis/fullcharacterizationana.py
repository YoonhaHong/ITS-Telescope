#!/usr/bin/env python3

import os
import csv
import argparse
import subprocess
import glob
import shutil
import datetime
    
def analyse_set(folder, sdict):
    output="Threshold:\n"
    # threshold
    # output+=subprocess.check_output(f"./thresholdana.py {folder+sdict['thr']+'.json'} --outdir {folder} -q --energy-factor 1", shell=True).decode("utf-8")
    output+=subprocess.check_output(f"./thresholdana.py {folder+sdict['thr']+'.json'} --outdir {folder} -q", shell=True).decode("utf-8")

    # decoding
    output+="\nDecoding:\n"
    output+=subprocess.check_output(f"./decodingana.py {folder+sdict['decoding']+'.json'} --outdir {folder} -q --save-calibration {folder+sdict['decoding']+'_falling.npy'} --falling-edge", shell=True).decode("utf-8")
    output+=subprocess.check_output(f"./decodingana.py {folder+sdict['decoding']+'.json'} --outdir {folder} -q --save-calibration {folder+sdict['decoding']+'_rising.npy'}", shell=True).decode("utf-8")
    
    # fhr
    output+="\nFHR:\n"
    output+=subprocess.check_output(f"./fhrana.py {folder+sdict['fhr']+'.json'} --outdir {folder} -q --decoding-calib {folder+sdict['decoding']+'_rising.npy'}", shell=True).decode("utf-8")

    # toa
    output+="\nToA:\n"
    output+=subprocess.check_output(f"./toatotana.py {folder+sdict['toa']+'.json'} --outdir {folder} -q --thrmapFile {folder+sdict['thr']+'_analyzed.npz'}", shell=True).decode("utf-8")
    
    # source decoder
    output+="\nSource Decoder:\n"
    output+=subprocess.check_output(f"./source_decoder.py {folder+sdict['source']+'.npy'} {folder+sdict['decoding']+'_rising.npy'} {folder+sdict['decoding']+'_falling.npy'} --outdir {folder} --plots", shell=True).decode("utf-8")
    
    # sourceana
    output+="\nSourceana:\n"
    output+=subprocess.check_output(f"./sourceana.py {folder+sdict['source']+'_decoded.npy'} --calToT {folder+os.path.basename(sdict['toa'])+'_analyzed.npz'} --outdir {folder} -q", shell=True).decode("utf-8")
    
    # energy calib
    output+="\nEnergy Calib:\n"
    try:
        output+=subprocess.check_output(f"./energy_calib.py {folder+sdict['source']+'_decoded_sourceana_analyzed.npz'} --outdir {folder} -q", shell=True).decode("utf-8")
    except subprocess.CalledProcessError as e:
        output+=("Energy fit didn't work on command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))
    return output


if __name__=="__main__":
    parser = argparse.ArgumentParser("Full chip analysis.")
    parser.add_argument("csvfile", help="CSV file created by the full characterization script.")
    args = parser.parse_args()

    filedict = {}
    folder = os.path.join(os.path.dirname(args.csvfile), "")
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    if os.path.exists(folder+"plots/"): 
        if glob.glob(folder+"plots/*"):
            # if not os.path.exists(folder+"old/"): os.makedirs(folder+"old/")
            if not os.path.exists(folder+f"old/old_{now}"): os.makedirs(folder+f"old/old_{now}/")
            for file in glob.glob(folder+"plots/*"):
                shutil.move(file, folder+f"old/old_{now}")
    else:
        os.makedirs(folder+"plots/")

    if os.path.exists(folder+"analysis_outputs/"): 
        if glob.glob(folder+"analysis_outputs/*"):
            # if not os.path.exists(folder+"old/"): os.makedirs(folder+"old/")
            if not os.path.exists(folder+f"old/old_{now}"): os.makedirs(folder+f"old/old_{now}/")
            for file in glob.glob(folder+"analysis_outputs/*"):
                shutil.move(file, folder+f"old/old_{now}")        
    else:
        os.makedirs(folder+"analysis_outputs/")

    with open(args.csvfile) as csv_file:
        for type, name in csv.reader(csv_file, delimiter=','):
            filedict[type] = name

    analysis_output = analyse_set(folder, filedict)

    for file in glob.glob(folder+"*.png"):
        shutil.move(file, folder+"plots")

    for file in glob.glob(folder+"pixel_plots"):
        shutil.move(file, folder+"plots")

    for file in glob.glob(folder+"*.npz*"):
        shutil.move(file, folder+"analysis_outputs")

    for file in glob.glob(folder+"*_decoded.npy"):
        shutil.move(file, folder+"analysis_outputs")

    for file in glob.glob(folder+"*_decoded.json"):
        shutil.move(file, folder+"analysis_outputs")

    for file in glob.glob(folder+"*_rising.npy"):
        shutil.move(file, folder+"analysis_outputs")
        
    for file in glob.glob(folder+"*_falling.npy"):
        shutil.move(file, folder+"analysis_outputs")

    with open(folder+"analysis_outputs/analysis_dump.log", "w") as ana_dump_file:
        ana_dump_file.write(analysis_output)