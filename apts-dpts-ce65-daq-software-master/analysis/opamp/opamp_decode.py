#!/usr/bin/env python3

__author__ = "Roberto Russo"
__maintainer__ = "Roberto Russo"
__email__ = "r.russo@cern.ch"
__status__ = "Development"

import numpy as np
from mlr1daqboard.opamp_decoder import OPAMPDecoder
import argparse
import json
from pathlib import Path


def raw_to_npz(fname_in,fname_out,n_scope_channels,scope_memory_depth,scope_data_precision,header):
    decoder = OPAMPDecoder(fname_in,n_scope_channels,scope_memory_depth,scope_data_precision,header)
    # ADC data
    adc_data = [decoder.get_next_adc_event()[0]]
    while not decoder.is_adc_done():
        adc_waveforms,_ = decoder.get_next_adc_event()
        assert adc_waveforms.shape == adc_data[0].shape, \
            f"Shape of the waveform array changed! {adc_waveforms.shape} != {adc_data[0].shape}"
        adc_data.append(adc_waveforms)
    # scope data
    scope_data = [decoder.get_next_scope_event()]
    while not decoder.is_scope_done():
        scope_waveforms = decoder.get_next_scope_event()
        assert scope_waveforms.shape == scope_data[0].shape, \
            f"Shape of the waveform array changed! {scope_waveforms.shape} != {scope_data[0].shape}"
        scope_data.append(scope_waveforms)
    np.savez(fname_out, ADC=adc_data, scope=scope_data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple example script for decoding APTS OA data taken with a supported oscilloscope.", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('file_in',help='File containing raw APTS OPAMP scope data.')
    parser.add_argument('--file_out',help='Outfile name. Default same name as input file but with npz extension.')
    parser.add_argument('--settings_file',required=True,help='.json file with oscilloscope settings used to take data. If "-1" is passed, default values are used.')
    parser.add_argument('--scope_data_precision',type=int,choices=[1, 2, 4],default=1,const=1,nargs='?',help='Number of bytes used to store scope waveform data. If not provided, 1 byte precision is assumed.')
    parser.add_argument('--scope_n_time_divisions',type=int,default=10,help='Number of time divisions in the oscilloscope screen.')
    parser.add_argument('--header','-hd', nargs='+',default=None,help='Remove the header by giving: byte in header  byte in footer  num pulses  num points scanned.')
    args = parser.parse_args()
    
    if args.header is not None:
        assert len(args.header)==4, f"Missing information in header. Only {len(args.header)} elements found: {args.header}. Expected arguments are:  byte in header  byte in footer  num pulses  num points scanned"
        
    if args.file_out == None:
        args.file_out = Path(args.file_in).with_suffix('.npz')
    if args.settings_file == -1:
        settings = {'ntrg': 100, 'inner_pixel_connections': {'1':'J5','2':'J6','3':'J9','4':'J10',}, 'time_division': 2e-09, 'scope_sampling_period': 0.0625e-9}
    else:
        with open(args.settings_file, 'r') as j:
            settings = json.load(j)
    n_points_scope_waveform = np.rint(args.scope_n_time_divisions*settings['time_division']/settings['scope_sampling_period'])
    raw_to_npz(args.file_in, args.file_out, len(settings['inner_pixel_connections'].keys()), n_points_scope_waveform, args.scope_data_precision, args.header)
