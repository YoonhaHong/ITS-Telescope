#!/usr/bin/env python3

import numpy as np
from pathlib import Path
import argparse
from mlr1daqboard import APTSDecoder
import re 
import json

def raw_to_npy(fname_in,fname_out,mux=False):
    decoder = APTSDecoder(fname_in, mux=mux)
    data = [decoder.get_next_event()[0]]
    while not decoder.is_done():
        waveforms,_ = decoder.get_next_event()
        assert waveforms.shape == data[0].shape, \
            f"Shape of the waveform array changed! {waveforms.shape} != {data[0].shape}"
        data.append(waveforms)
    np.save(fname_out,data)

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Simple example script for APTS decoding")
    parser.add_argument('file_in',help='File containing raw APTS data. This is also used to read a .json file with the same name.')
    parser.add_argument('--file_out',help='Outfile name. Default same name as input file but with npy extension.')
    args = parser.parse_args()

    if args.file_out == None:
        args.file_out = Path(args.file_in).with_suffix('.npy')

    mux = False
    if Path(args.file_in).with_suffix('.json').is_file():
        with open(Path(args.file_in).with_suffix('.json'), 'r') as file_json:
            data_json = json.load(file_json)
            if 'chip_ID' in data_json:
                chip_ID = data_json['chip_ID']
                extract_name_volt = re.match(r"[E]?[R]?[1]?A[AF]([12]?[05]?)([BP])?([M])?_(W\d{2})(B\d{1})", chip_ID)
                mux = True if extract_name_volt.group(3)=="M" else False
    else:
        print("WARNING, " + Path(args.file_in).with_suffix('.json') + " not found, assuming mux=False!")
    
    if Path(args.file_out).suffix=='.npy':
        raw_to_npy(args.file_in,args.file_out,mux=mux)
    else:
        print("ERROR, unknown file format!")
