#!/usr/bin/env python3

# Isabella Sanna, 03/2022, CERN
# Python script that decodes the raw data acquired during all the scans of all paramters for APTS. The output is a CSV file.

import argparse
import mlr1daqboard
from mlr1daqboard import APTSDecoder
import numpy as np
import os
import re
from pathlib import Path
import json

def list_files(dir): # function used to list all the files present inside all the subdirecotries of a directory (given in input)
    r = []
    for subdir,_,files in os.walk(dir):
        for file in files:
            r.append(os.path.join(subdir, file))
    return r

parser = argparse.ArgumentParser(description="Script for the decoding of the data acquired during the APTS parameters scan.")
parser.add_argument('directory', default='../../Data/scan_operating_point', help='directory of file containing scan data.')
args = parser.parse_args()

for file in list_files(args.directory):
    if file.endswith('.raw') and os.path.isfile(file.replace('.raw','.csv'))==False:     # if the raw file was already decoded does not repeat the decoding 
        fout = open(file.replace('.raw','.csv'),'w' )
        fout.write('# '+','.join(' '.join(l.strip().split(' ')[-4:]).replace('to','=') for l in open(file.replace('raw','log'), 'r') if 'Sett' in l and ('uA' in l or 'mV' in l))+'\n') # Header with parameters values

        mux = False
        if Path(file).with_suffix('.json').is_file():
            with open(Path(file).with_suffix('.json'), 'r') as file_json:
                data_json = json.load(file_json)
                if 'chip_ID' in data_json:
                    chip_ID = data_json['chip_ID']
                    extract_name_volt = re.match(r"A[AF]([12]?[05]?)([BP])?([M])?_(W\d{2})(B\d{1})", chip_ID)
                    mux = True if extract_name_volt.group(3)=="M" else False
        else:
            print("WARNING, " + Path(file).with_suffix('.json') + " not found, assuming mux=False!")
        decoder = APTSDecoder(file, mux=mux)

        i=1

        while(not decoder.is_done()):
            waveforms,tst = decoder.get_next_event()
            waveforms = waveforms.T
            waveforms = waveforms.reshape(waveforms.shape[0],16)
            iarr = np.array([i]*len(waveforms)) #index of events
            np.savetxt(fout, np.concatenate([iarr[:,np.newaxis], np.arange(len(waveforms))[:,np.newaxis], waveforms], axis=1), fmt='%d') #write in output-file the waveforms, indexed by number of event and number of frame
            i+=1
        fout.close()
