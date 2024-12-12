# this is a python script

#=======================================================================
#   Copyright (C) 2023 Univ. of Bham  All rights reserved.
#   
#   		FileName：		apts_leakage_calibration.py
#   	 	Author：		LongLI <long.l@cern.ch>
#   		Time：			2023.10.22
#   		Description：
#
#======================================================================

import os
import sys
import argparse

def do_calibration(gain_path, tr, vbbr, ir):
    print(f'Gain calibration analysis from {gain_path}')
    cmd = f'python3 ../../analysis/apts/analysis_gain.py {gain_path}'
    os.system(cmd)
    
    for temp in tr:
        for vbb in vbbr:
            for irst in ir:
                vbb_k = int(vbb*1000)
                ir_k = int(irst*1000)
                for path,  _, _, in os.walk(gain_path):
                    if vbb == 0.0: vbb = 0
                    if 'temp'+str(temp) in path and 'vbb_'+str(vbb) in path and 'ir_'+str(irst) in path:
                        for _, _, files in os.walk(path):
                            data_calib, data_raw, data_npy = '', '', ''
                            for file in files:
                                if file.endswith('_analysed.npz'):
                                    data_calib = os.path.join(path, file)
                            
                            if data_calib == None: continue
                                
                            # find data
                            data_path = gain_path+'/data'
                            for _, _, files, in os.walk(data_path):
                                for file in files:
                                    label_v, label_ir, label_t = f'vbb{vbb_k}', f'ir{ir_k}', f'T{temp}'
                                    if label_v in file and label_ir in file and label_t in file:
                                        if file.endswith('.raw'): 
                                            data_raw = os.path.join(data_path, file) 
                                            data_npy = data_raw.replace('.raw', '.npy')
                                        
                                        if not os.path.exists(data_npy) and data_raw != '':
                                            cmd = f'python3 ../../analysis/apts/apts_decode.py {data_raw}'
                                            os.system(cmd)

                                        # signal calibration
                                        cmd = f'python3 ../../analysis/apts/signal_calibration.py {data_npy} {data_calib} -d {data_path}'
                                        print('Starting with:', temp, 'C,', vbb, 'V,', irst, 'uA')
                                        os.system(cmd)

    print(f'============================CALIBRATION DONE=============================')

def apts_leakage_calibration(args):
    if args.proximity == 'All' or args.chip == 'All':
        for path, cDir, files in os.walk(args.data):
            if 'data' in path:
                gain_path = path.replace('data', '')
                do_calibration(gain_path, args.temp_range, args.vbb_range, args.ireset_range)
    else:
        gain_path = args.data + '/' + args.proximity + '/' + args.chip
        do_calibration(gain_path, args.temp_range, args.vbb_range, args.ireset_range)
    



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parameters for APTS SF leakage data calibration')
    parser.add_argument('--data', '-d', type=str, default='../../Data', help='Directory to APTS data')
    parser.add_argument('--proximity', '-prox', type=str, default='All', help='Proximity for the measurements')
    parser.add_argument('--chip', '-c', type=str, default='All', help='whcih data to be calibrated')
    parser.add_argument('--temp_range', '-tr', type=int, nargs='+', default=[20, 21, 22, 23, 24], help='Temperature range of the calibration')
    parser.add_argument('--vbb_range', '-vbbr', type=float, nargs='+', default=[0.0, 1.2, 2.4, 3.6, 4.8], help='Vbb range of the calibration')
    parser.add_argument('--ireset_range', '-irr', type=float, nargs='+', default=[0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6], help='Reset current range of the calibration')
    args = parser.parse_args()
    apts_leakage_calibration(args)
