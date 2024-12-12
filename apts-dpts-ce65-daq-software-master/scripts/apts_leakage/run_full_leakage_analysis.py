# this is a python script

#=======================================================================
#   Copyright (C) 2023 Univ. of Bham  All rights reserved.
#   
#   		FileName：		run_full_analysis.py
#   	 	Author：		LongLI <long.l@cern.ch>
#   		Time：			2023.10.25
#   		Description：
#
#======================================================================

import os
import sys
import argparse

def run_full_leakage_analysis(args):
    for path, _, _ in os.walk(args.data):
        if 'data' in path:
            args.chip = path.split('/')[-2]
            args.proximity = path.split('/')[-3]
            args.directory = args.data+'/'+args.proximity+'/'+args.chip
            if 'AF15' in args.chip:
                cmd = f'python3 apts_leakage_calibration.py -prox {args.proximity} -c {args.chip} '
                os.system(cmd)
                cmd = f'python3 apts_leakage_fit.py -prox {args.proximity} -c {args.chip}'
                os.system(cmd)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parameters for leakage analysis full run')
    parser.add_argument('--data', '-d', default='../../Data', help='Directory for input files')
    parser.add_argument('--temp_range', '-tr', type=int, nargs='+', default=[20, 21], help='Temperature range of the calibration')
    parser.add_argument('--vbb_range', '-vbbr', type=float, nargs='+', default=[0.0, 1.2, 2.4, 3.6, 4.8], help='Vbb range of the calibration')
    parser.add_argument('--ireset_range', '-irr', type=float, nargs='+', default=[0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6], help='Reset current range of the calibration')
    args = parser.parse_args()
    run_full_leakage_analysis(args)
